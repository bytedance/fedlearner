# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import os
import threading
import uuid
import time
import logging
from contextlib import contextmanager

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from fedlearner.data_join.example_id_visitor import (
    ExampleIdManager, encode_example_id_dumped_fname
)
from fedlearner.data_join import visitor

class ExampleIdDumperManager(object):
    class ExampleIdDumper(object):
        def __init__(self, process_index, start_index,
                     example_dumped_dir, dump_threshold):
            self._process_index = process_index
            self._start_index = start_index
            self._end_index = start_index - 1
            self._example_dumped_dir = example_dumped_dir
            self._dump_threshold = dump_threshold
            self._tmp_fpath = self._get_tmp_fpath()
            self._tf_record_writer = tf.io.TFRecordWriter(self._tmp_fpath)
            self._dumped_example_id_batch_count = 0

        def dump_example_id_batch(self, example_id_batch):
            if len(example_id_batch.example_id) == 0:
                logging.warning("skip example id batch since empty")
                return
            assert self._end_index + 1 == example_id_batch.begin_index, \
                "the recv example id index should be consecutive, {} + 1 "\
                "!= {}".format(self._end_index, example_id_batch.begin_index)
            assert len(example_id_batch.example_id) == \
                    len(example_id_batch.event_time), \
                    "the size example id and envet time shoud the same"
            self._tf_record_writer.write(example_id_batch.SerializeToString())
            self._end_index += len(example_id_batch.example_id)
            self._dumped_example_id_batch_count += 1

        def check_dumper_full(self):
            dump_count = self._end_index - self._start_index + 1
            if self._dump_threshold > 0 and \
                    dump_count > self._dump_threshold:
                return True
            return False

        def finish_example_id_dumper(self):
            self._tf_record_writer.close()
            if self.dumped_example_id_count() > 0:
                fpath = self._get_dumped_fpath()
                gfile.Rename(self._tmp_fpath, fpath, True)
                index_meta = visitor.IndexMeta(
                        self._process_index, self._start_index, fpath
                    )
                return index_meta, self._end_index
            assert self._start_index == self._end_index, "no example id dumped"
            gfile.Remove(self._tmp_fpath)
            return None, None

        def __del__(self):
            if self._tf_record_writer is not None:
                del self._tf_record_writer
            self._tf_record_writer = None

        def dumped_example_id_count(self):
            return self._end_index - self._start_index + 1

        def dumped_example_id_batch_count(self):
            return self._dumped_example_id_batch_count

        def _get_dumped_fpath(self):
            fname = encode_example_id_dumped_fname(self._process_index,
                                                   self._start_index)
            return os.path.join(self._example_dumped_dir, fname)

        def _get_tmp_fpath(self):
            tmp_fname = str(uuid.uuid1()) + '-dump.tmp'
            return os.path.join(self._example_dumped_dir, tmp_fname)

    def __init__(self, etcd, data_source,
                 partition_id, example_id_dump_options):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._dump_interval = \
                example_id_dump_options.example_id_dump_interval
        self._dump_threshold = \
                example_id_dump_options.example_id_dump_threshold
        self._fly_example_id_batch = []
        self._example_id_sync_finished = False
        self._latest_dump_timestamp = time.time()
        self._example_id_manager = \
                ExampleIdManager(etcd, data_source, partition_id, False)
        last_index = self._example_id_manager.get_last_dumped_index()
        self._next_index = 0 if last_index is None else last_index + 1
        self._example_id_dumper = None
        self._state_stale = False

    def get_next_index(self):
        with self._lock:
            return self._next_index

    def add_example_id_batch(self, example_id_batch):
        with self._lock:
            if self._example_id_sync_finished:
                raise RuntimeError(
                        "sync example for partition {} has "\
                        "finished".format(self._partition_id)
                    )
            assert example_id_batch.partition_id == self._partition_id, \
                "the partition id of recv example batch mismatch with " \
                "dumping example id: {} != {}".format(
                    self._partition_id, example_id_batch.partition_id
                )
            if example_id_batch.begin_index != self._next_index:
                return False, self._next_index
            num_example = len(example_id_batch.example_id)
            self._fly_example_id_batch.append(example_id_batch)
            self._next_index = example_id_batch.begin_index + num_example
            return True, self._next_index

    @contextmanager
    def make_example_id_dumper(self):
        self._sync_with_example_id_manager()
        self._acquire_state_stale()
        yield self._dump_example_id_impl
        self._release_state_stale()

    def need_dump(self):
        with self._lock:
            if len(self._fly_example_id_batch) > 0:
                return True
            return self._need_finish_dumper(self._example_id_sync_finished)

    def finish_sync_example_id(self):
        with self._lock:
            self._example_id_sync_finished = True

    def is_sync_example_id_finished(self):
        with self._lock:
            return self._example_id_sync_finished

    def _dump_example_id_impl(self):
        while self.need_dump():
            self._dump_one_example_id_batch()
            is_batch_finisehd = self._is_batch_finished()
            if self._need_finish_dumper(is_batch_finisehd):
                self._finish_example_id_dumper()

    def _acquire_state_stale(self):
        with self._lock:
            self._state_stale = True

    def _release_state_stale(self):
        with self._lock:
            self._state_stale = False

    def _dump_one_example_id_batch(self):
        batch_index = 0 if self._example_id_dumper is None else \
                self._example_id_dumper.dumped_example_id_batch_count()
        example_id_batch = \
                self._get_synced_example_id_batch(batch_index)
        if example_id_batch is not None:
            dumper = self._get_example_id_dumper(True)
            dumper.dump_example_id_batch(example_id_batch)

    def _need_finish_dumper(self, is_batch_finished):
        duration_since_dump = time.time() - self._latest_dump_timestamp
        if self._example_id_dumper is not None and \
                (self._example_id_dumper.check_dumper_full() or \
                 is_batch_finished or
                 0 < self._dump_interval <= duration_since_dump):
            return True
        return False

    def _is_batch_finished(self):
        with self._lock:
            if not self._example_id_sync_finished:
                return False
            dumped_batch_count = 0 if self._example_id_dumper is None else \
                    self._example_id_dumper.dumped_example_id_batch_count()
            return dumped_batch_count == len(self._fly_example_id_batch)

    def _finish_example_id_dumper(self):
        dumper = self._get_example_id_dumper(False)
        assert dumper is not None, "example id dumper must not None"
        index_meta, end_index = dumper.finish_example_id_dumper()
        if index_meta is not None and end_index is not None:
            self._example_id_manager.update_dumped_example_id_anchor(
                    index_meta, end_index
                )
        self._evict_dumped_example_id_batch()
        self._reset_example_id_dumper()
        self._update_latest_dump_timestamp()

    def _update_latest_dump_timestamp(self):
        with self._lock:
            self._latest_dump_timestamp = time.time()

    def _is_state_stale(self):
        with self._lock:
            return self._state_stale

    def _get_synced_example_id_batch(self, batch_index):
        with self._lock:
            assert batch_index >= 0, "batch index should be >= 0"
            if len(self._fly_example_id_batch) <= batch_index:
                return None
            return self._fly_example_id_batch[batch_index]

    def _sync_with_example_id_manager(self):
        if self._is_state_stale():
            self._evict_dumped_example_id_batch()
            self._reset_example_id_dumper()

    def _get_example_id_dumper(self, create_if_no_existed):
        if self._example_id_dumper is None and create_if_no_existed:
            last_index = self._example_id_manager.get_last_dumped_index()
            next_index = 0 if last_index is None else last_index + 1
            dumper = self.ExampleIdDumper(
                    self._example_id_manager.get_next_process_index(),
                    next_index,
                    self._example_id_manager.get_example_dumped_dir(),
                    self._dump_threshold
                )
            with self._lock:
                self._example_id_dumper = dumper
        return self._example_id_dumper

    def _evict_dumped_example_id_batch(self):
        last_index = self._example_id_manager.get_last_dumped_index()
        next_index = 0 if last_index is None else last_index + 1
        with self._lock:
            skip_count = 0
            for example_id_batch in self._fly_example_id_batch:
                example_id_count = len(example_id_batch.example_id)
                end_index = example_id_batch.begin_index + example_id_count
                if end_index > next_index:
                    assert example_id_batch.begin_index == next_index, \
                        "the dumped example id should align with "\
                        "recv example id batch"
                    break
                skip_count += 1
            self._fly_example_id_batch = \
                    self._fly_example_id_batch[skip_count:]

    def _reset_example_id_dumper(self):
        dumper = None
        with self._lock:
            dumper = self._example_id_dumper
            self._example_id_dumper = None
        if dumper is not None:
            del dumper
