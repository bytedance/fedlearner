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
import logging

import tensorflow as tf
from tensorflow.python.platform import gfile

from fedlearner.data_join.example_id_visitor import (
        ExampleIdManager, ExampleIdMeta
)
from fedlearner.data_join.common import ExampleIdSuffix
from fedlearner.common import data_join_service_pb2 as dj_pb

class ExampleIdDumperManager(object):
    class ExampleIdDumper(object):
        def __init__(self, start_index, example_dumped_dir):
            self._start_index = start_index
            self._end_index = start_index - 1
            self._example_dumped_dir = example_dumped_dir
            self._tmp_fpath = self._get_tmp_fpath()
            self._tf_record_writer = (
                tf.io.TFRecordWriter(self._tmp_fpath))
            self._fly_dumpped_example_req = []

        def dump_synced_example(self, synced_example_req):
            assert self._end_index + 1 == synced_example_req.begin_index
            assert (len(synced_example_req.example_id) ==
                        len(synced_example_req.event_time))
            self._fly_dumpped_example_req.append(synced_example_req)
            for idx, example_id in enumerate(synced_example_req.example_id):
                self._end_index += 1
                event_time = synced_example_req.event_time[idx]
                syned_example_id = dj_pb.SyncedExampleId()
                syned_example_id.example_id = example_id
                syned_example_id.event_time = event_time
                syned_example_id.index = self._end_index
                self._tf_record_writer.write(
                    syned_example_id.SerializeToString())

        def finish_example_id_dumper(self):
            self._tf_record_writer.close()
            self._tf_record_writer = None
            if self.dumped_example_number() > 0:
                fpath = self._get_dumped_fpath()
                gfile.Rename(self._tmp_fpath, fpath)
                return ExampleIdMeta(self._start_index, self._end_index, fpath)
            assert self._start_index == self._end_index
            gfile.Remove(self._tmp_fpath)
            return None

        def __del__(self):
            if self._tf_record_writer is not None:
                self._tf_record_writer.close()
            del self._tf_record_writer
            self._tf_record_writer = None

        def dumped_example_number(self):
            return self._end_index - self._start_index + 1

        def get_fly_req(self):
            return self._fly_dumpped_example_req

        def _get_dumped_fpath(self):
            fname = '{}-{}{}'.format(self._start_index,
                                     self._end_index, ExampleIdSuffix)
            return os.path.join(self._example_dumped_dir, fname)

        def _get_tmp_fpath(self):
            tmp_fname = str(uuid.uuid1()) + '-dump.tmp'
            return os.path.join(self._example_dumped_dir, tmp_fname)

    def __init__(self, data_source, partition_id):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._fly_synced_example_req = []
        self._synced_example_finished = False
        self._example_id_manager = ExampleIdManager(data_source, partition_id)
        self._next_index = self._example_id_manager.get_next_index()
        self._example_id_dumper = None
        self._stale_with_dfs = False

    def get_next_index(self):
        with self._lock:
            return self._next_index

    def get_partition_id(self):
        with self._lock:
            return self._partition_id

    def append_synced_example_req(self, req):
        with self._lock:
            if self._synced_example_finished:
                raise RuntimeError(
                        "sync example for partition {} has "\
                        "finished".format(self._partition_id)
                    )
            if req.begin_index != self._next_index:
                return (False, self._next_index)
            num_example = len(req.example_id)
            self._fly_synced_example_req.append(req)
            self._next_index = req.begin_index + num_example
            return (True, self._next_index)

    def dump_example_ids(self):
        try:
            self._sync_with_dfs()
            while True:
                finished = False
                req = None
                dumper = None
                with self._lock:
                    finished, req = self._get_next_synced_example_req()
                    if req is not None:
                        dumper = self._get_example_id_dumper()
                    if finished:
                        dumper = self._example_id_dumper
                if req is not None:
                    assert dumper is not None
                    dumper.dump_synced_example(req)
                if dumper is not None:
                    dumped_num = dumper.dumped_example_number()
                    if dumped_num >= (1 << 16) or finished:
                        meta = dumper.finish_example_id_dumper()
                        with self._lock:
                            assert dumper == self._example_id_dumper
                            self._example_id_dumper = None
                            manager = self._example_id_manager
                            if meta is not None:
                                manager.append_dumped_id_meta(meta)
                if req is None:
                    break
        except Exception as e: # pylint: disable=broad-except
            logging.error("Failed to dump example id for partition %d",
                           self._partition_id)
            with self._lock:
                # rollback the fly syned example req
                if self._example_id_dumper is not None:
                    fly_reqs = self._example_id_dumper.get_fly_req()
                    self._fly_synced_example_req = (
                        fly_reqs + self._fly_synced_example_req)
                del self._example_id_dumper
                self._example_id_dumper = None
                self._stale_with_dfs = True

    def need_dump(self):
        with self._lock:
            return (len(self._fly_synced_example_req) > 0 or
                    self._stale_with_dfs or
                    (self._example_id_dumper is not None and
                        self._synced_example_finished))

    def finish_sync_example(self):
        with self._lock:
            self._synced_example_finished = True

    def example_sync_finished(self):
        with self._lock:
            return self._synced_example_finished

    def _get_next_synced_example_req(self):
        if len(self._fly_synced_example_req) == 0:
            if self._synced_example_finished:
                return True, None
            return False, None
        return False, self._fly_synced_example_req.pop(0)


    def _get_example_id_dumper(self):
        if self._example_id_dumper is None:
            next_index = self._example_id_manager.get_next_index()
            self._example_id_dumper = self.ExampleIdDumper(
                    next_index,
                    self._example_id_manager.get_example_dumped_dir()
                )
        return self._example_id_dumper

    def _sync_with_dfs(self):
        if self._stale_with_dfs:
            self._example_id_manager.sync_dumped_meta_with_dfs()
            next_index = self._example_id_manager.get_next_index()
            with self._lock:
                skip_count = 0
                for req in self._fly_synced_example_req:
                    num_example = len(req.example_id)
                    if req.begin_index + num_example > next_index:
                        break
                    skip_count += 1
                self._fly_synced_example_req = (
                        self._fly_synced_example_req[skip_count:])
            self._stale_with_dfs = False
