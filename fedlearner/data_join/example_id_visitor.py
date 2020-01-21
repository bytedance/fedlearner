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

import logging
import os
import threading
import bisect
import ntpath

from tensorflow.python.platform import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.common import ExampleIdSuffix, make_tf_record_iter

class ExampleIdMeta(object):
    def __init__(self, start_index, end_index, fpath):
        self.start_index = start_index
        self.end_index = end_index
        self.fpath = fpath
        assert self.end_index >= self.start_index

    def __lt__(self, other):
        return self.start_index < other.start_index

    def __eq__(self, other):
        return (self.start_index == other.start_index and
                self.end_index == other.end_index and
                self.fpath == other.fpath)

class ExampleIdManager(object):
    def __init__(self, data_source, partition_id):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._next_index = 0
        self._dumped_example_id_meta = []
        self._sync_dumped_example_id_meta()

    def get_dumped_example_id_meta(self):
        with self._lock:
            return self._dumped_example_id_meta

    def get_example_id_meta_by_index(self, index):
        with self._lock:
            if index >= len(self._dumped_example_id_meta):
                return None
            return self._dumped_example_id_meta[index]

    def get_next_index(self):
        with self._lock:
            return self._next_index

    def append_dumped_id_meta(self, meta):
        with self._lock:
            if len(self._dumped_example_id_meta) == 0:
                if meta.start_index != 0:
                    raise RuntimeError(
                            "first dumped example ids should start from 0"
                        )
            else:
                prev_meta = self._dumped_example_id_meta[-1]
                if prev_meta.end_index+1 != meta.start_index:
                    raise RuntimeError("the example index is not consecutive")
            self._dumped_example_id_meta.append(meta)
            self._next_index = meta.end_index + 1

    def sync_dumped_meta_with_dfs(self):
        with self._lock:
            self._sync_dumped_example_id_meta()

    def get_example_dumped_dir(self):
        return self._example_dumped_dir()

    def _sync_dumped_example_id_meta(self):
        fpaths = self._list_example_dumped_dir()
        self._dumped_example_id_meta = []
        for fpath in fpaths:
            meta = self._parse_meta_from_fname(fpath)
            if meta is None:
                gfile.Remove(fpath)
            else:
                self._dumped_example_id_meta.append(meta)
        self._dumped_example_id_meta.sort()
        for (idx, meta) in enumerate(self._dumped_example_id_meta):
            if idx == 0:
                if meta.start_index != 0:
                    logging.fatal("the example index shoud start from 0")
                    os._exit(-1) # pylint: disable=protected-access
            elif (meta.start_index !=
                    self._dumped_example_id_meta[idx-1].end_index+1):
                logging.fatal('index of example is not consecutive')
                os._exit(-1) # pylint: disable=protected-access
        if len(self._dumped_example_id_meta) > 0:
            meta = self._dumped_example_id_meta[-1]
            self._next_index = meta.end_index + 1
        else:
            self._next_index = 0

    def _list_example_dumped_dir(self):
        example_dir = self._example_dumped_dir()
        if not gfile.Exists(example_dir):
            gfile.MakeDirs(example_dir)
        fpaths = [os.path.join(example_dir, f)
                    for f in gfile.ListDirectory(example_dir)
                    if not gfile.IsDirectory(os.path.join(example_dir, f))]
        fpaths.sort()
        return fpaths

    def _example_dumped_dir(self):
        return os.path.join(self._data_source.example_dumped_dir,
                            'partition_{}'.format(self._partition_id))

    @staticmethod
    def _parse_meta_from_fname(fpath):
        fname = ntpath.basename(fpath)
        if not fname.endswith(ExampleIdSuffix):
            return None
        index_str = fname[0:-len(ExampleIdSuffix)].split('-')
        if len(index_str) != 2:
            logging.warning('%s is not a dumped example file', fname)
            return None
        try:
            start_index, end_index = int(index_str[0]), int(index_str[1])
        except Exception as e: # pylint: disable=broad-except
            logging.warning("Failed to extract start, end index "\
                            "from %s", fname)
            return None
        return ExampleIdMeta(start_index, end_index, fpath)

class ExampleIdVisitor(object):
    class ExampleIdIter(object):
        def __init__(self):
            self._meta = None
            self._index = None
            self._example_id = None
            self._fiter = None

        def reset_iter(self, meta=None):
            self._meta = None
            self._index = None
            self._fiter = None
            self._example_id = None
            if meta is not None:
                fiter = self._inner_iter(meta.fpath)
                example_id = next(fiter)
                self._example_id = example_id
                self._index = meta.start_index
                self._fiter = fiter
                self._meta = meta

        def seek_to_target(self, target_index):
            self._check_valid()
            if (self._meta.start_index > target_index or
                    self._meta.end_index < target_index):
                raise IndexError("target index is out of range")
            if self._index > target_index:
                self.reset_iter(self._meta)
            assert self._index <= target_index
            if self._index == target_index:
                return self._index, self._example_id
            for example_id in self._fiter:
                self._example_id = example_id
                self._index += 1
                if self._index == target_index:
                    break
            return self._index, self._example_id

        def __iter__(self):
            return self

        def __next__(self):
            self._check_valid()
            self._example_id = next(self._fiter)
            self._index += 1
            return self._index, self._example_id

        def next(self):
            return self.__next__()

        def _inner_iter(self, fpath):
            with make_tf_record_iter(fpath) as record_iter:
                for record in record_iter:
                    example_id = dj_pb.SyncedExampleId()
                    example_id.ParseFromString(record)
                    yield example_id

        def _check_valid(self):
            assert self._meta is not None
            assert self._index is not None
            assert self._example_id is not None
            assert self._fiter is not None

    def __init__(self, example_id_manager):
        self._example_id_manager = example_id_manager
        self._current_meta_index = 0
        self._exampld_id_iter = None
        self._dumped_example_id_meta = []
        self._dumped_example_id_meta = (
            self._example_id_manager.get_dumped_example_id_meta())
        self._finished = False
        for (idx, meta) in enumerate(self._dumped_example_id_meta):
            if idx == 0:
                if meta.start_index != 0:
                    logging.fatal("example id index is not start from 0")
                    os._exit(-1)
            else:
                prev_meta = self._dumped_example_id_meta[idx-1]
                if prev_meta.end_index+1 != meta.start_index:
                    logging.fatal("index of example id is not consecutive")
                    os._exit(-1)

    def seek(self, target):
        self._finished = False
        tmp_meta = ExampleIdMeta(target, target, '')
        idx = bisect.bisect_left(self._dumped_example_id_meta, tmp_meta)
        if idx > 0 and self._dumped_example_id_meta[idx-1].end_index >= target:
            idx -= 1
        if idx >= len(self._dumped_example_id_meta):
            self._finished = True
            raise StopIteration()
        if idx < 0:
            raise IndexError("target {} is out of range".format(target))
        self._current_meta_index = idx
        if self._exampld_id_iter is None:
            self._exampld_id_iter = ExampleIdVisitor.ExampleIdIter()
        self._exampld_id_iter.reset_iter(self._dumped_example_id_meta[idx])
        return self._exampld_id_iter.seek_to_target(target)

    def finished(self):
        return self._finished

    def __iter__(self):
        return self

    def __next__(self):
        try:
            if self._exampld_id_iter is None:
                raise StopIteration()
            return next(self._exampld_id_iter)
        except StopIteration:
            if self._exampld_id_iter is None:
                self._current_meta_index = 0
            else:
                self._current_meta_index += 1
            if self._current_meta_index == len(self._dumped_example_id_meta):
                self._finished = True
                raise StopIteration()
            meta = self._dumped_example_id_meta[self._current_meta_index]
            if self._exampld_id_iter is None:
                self._exampld_id_iter = ExampleIdVisitor.ExampleIdIter()
            self._exampld_id_iter.reset_iter(meta)
            return self._exampld_id_iter.seek_to_target(meta.start_index)

    def next(self):
        return self.__next__()
