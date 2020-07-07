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
import random
import logging
try:
    import queue
except ImportError:
    import Queue as queue

from tensorflow.compat.v1 import gfile
import tensorflow as tf

from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfRecordIter
from fedlearner.data_join import visitor, common

class Merge(object):
    class RecordItem(object):
        def __init__(self, fpath_id, tf_example_item):
            self._fpath_id = fpath_id
            self._tf_example_item = tf_example_item

        @property
        def fpath_id(self):
            return self._fpath_id

        @property
        def tf_example_item(self):
            return self._tf_example_item

        def __lt__(self, other):
            assert isinstance(other, Merge.RecordItem)
            return self._tf_example_item.event_time < \
                    other.tf_example_item.event_time

    class InputFileReader(object):
        def __init__(self, fpath_id, fpath, options):
            self._fpath_id = fpath_id
            self._fpath = fpath
            self._raw_data_options = options.raw_data_options
            self._fiter = None
            if gfile.Exists(fpath):
                self._finished = False
            else:
                self._finished = True

        @property
        def finished(self):
            return self._finished

        def __iter__(self):
            return self

        def __next__(self):
            return self._next_internal()

        def next(self):
            return self._next_internal()

        def _next_internal(self):
            if not self._finished:
                try:
                    while True:
                        tf_item = None
                        if self._fiter is None:
                            self._fiter = TfRecordIter(self._raw_data_options)
                            meta = visitor.IndexMeta(0, 0, self._fpath)
                            self._fiter.reset_iter(meta, True)
                            tf_item = self._fiter.get_item()
                        else:
                            _, tf_item = next(self._fiter)
                        return Merge.RecordItem(self._fpath_id, tf_item)
                except StopIteration:
                    self._finished = True
            raise StopIteration("%s has been iter finished" % self._fpath)

    class FileMeta(object):
        def __init__(self, partition_id, begin_index, end_index):
            self._partition_id = partition_id
            self._begin_index = begin_index
            self._end_index = end_index

        def encode_meta_to_fname(self):
            return '{:04}.{:010}-{:010}{}'.format(
                self._partition_id, self._begin_index,
                self._end_index, common.RawDataFileSuffix)


    class OutputFileWriter(object):
        def __init__(self, options, partition_id):
            self._partition_id = partition_id
            self._writer = None
            self._begin_index = None
            self._end_index = None
            self._options = options
            self._size_bytes = 0
            self._tmp_fpath = common.gen_tmp_fpath(
                os.path.join(self._options.output_dir,
                    common.partition_repr(self._partition_id))
            )

        def append_item(self, item, index):
            writer = self._get_output_writer()
            tf_item = item.tf_record
            writer.write(tf_item)
            if self._begin_index is None:
                self._begin_index = index
            self._end_index = index
            self._size_bytes += len(tf_item)
            if self._size_bytes >= self._options.output_item_threshold:
                writer.close()
                self.writer = None
                meta = Merge.FileMeta(self._partition_id, self._begin_index,
                    self._end_index)
                fpath = os.path.join(self._options.output_dir,
                    common.partition_repr(self._partition_id),
                    meta.encode_meta_to_fname())
                gfile.Rename(self.get_tmp_fpath(), fpath, True)
                self._size_bytes = 0
                self._begin_index = None
                self._end_index = None
                self._writer = None

        def finish(self):
            if self._begin_index is not None \
                and self._end_index is not None:
                self._writer.close()
                meta = Merge.FileMeta(self._partition_id, self._begin_index,
                    self._end_index)
                fpath = os.path.join(self._options.output_dir,
                    common.partition_repr(self._partition_id),
                    meta.encode_meta_to_fname())
                gfile.Rename(self.get_tmp_fpath(), fpath, True)
                self._writer = None

        def get_tmp_fpath(self):
            return self._tmp_fpath

        def _get_output_writer(self):
            if self._writer is None:
                self._new_writer()
            return self._writer

        def _new_writer(self):
            assert self._writer is None
            self._writer = tf.io.TFRecordWriter(self._tmp_fpath)


    def __init__(self, options, partition_id):
        self._readers = []
        self._options = options
        self._partition_id = partition_id
        self._queue = queue.PriorityQueue(options.merge_buffer_size)
        self._active_fpath = set()
        self._fpaths = gfile.ListDirectory(self._options.input_dir)
        self._fpath_num = len(self._fpaths)
        self._writer = Merge.OutputFileWriter(self._options, self._partition_id)
        self._prepare()

    def _prepare(self):
        self._output_dir = os.path.join(self._options.output_dir,
            common.partition_repr(self._partition_id))
        if gfile.Exists(self._output_dir):
            gfile.DeleteRecursively(self._output_dir)
        gfile.MkDir(self._options.output_dir)
        gfile.MkDir(self._output_dir)
        for fpath_id, fpath in enumerate(self._fpaths):
            fpath = "{}/{}".format(self._options.input_dir, fpath)
            reader = Merge.InputFileReader(fpath_id,
                fpath, self._options)
            self._readers.append(reader)
            self._active_fpath.add(fpath_id)
            logging.info("Merge partition_id:%d, path:%s", 
                self._partition_id, fpath)
        self._preload_queue()

    def _preload_queue(self):
        fpath_id = 0
        size_active = len(self._active_fpath)
        while not self._queue.full() and size_active > 0:
            if fpath_id not in self._active_fpath:
                continue
            self._replenish_item(fpath_id)
            fpath_id = (fpath_id + 1) % self._fpath_num

    def _replenish_item(self, fpath_id):
        assert not self._queue.full(), \
            "Priority Queue should not full duration replenish_item"
        while len(self._active_fpath) > 0:
            if fpath_id in self._active_fpath:
                for item in self._readers[fpath_id]:
                    self._queue.put(item)
                    return
                assert self._readers[fpath_id].finished
                self._active_fpath.discard(fpath_id)
            if len(self._active_fpath) > 0:
                fpath_id = random.choice(list(self._active_fpath))

    def finish(self):
        success_path = "{}/{}".format(self._output_dir, "_SUCCESS")
        with gfile.GFile(success_path, 'w') as f:
            f.write("")

    def generate_output(self):
        index = 0
        while not self._queue.empty():
            record_item = self._queue.get()
            self._replenish_item(record_item.fpath_id)
            self._writer.append_item(record_item.tf_example_item, index)
            index += 1
        self._writer.finish()
