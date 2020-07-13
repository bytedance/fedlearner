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

import threading
import logging
import os

from tensorflow.compat.v1 import gfile

from fedlearner.data_join.common import encode_data_block_meta_fname, \
                                        partition_repr, load_data_block_meta

class DataBlockManager(object):
    def __init__(self, data_source, partition_id):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._data_block_meta_cache = {}
        self._dumped_index = None
        self._dumping_index = None
        self._make_directory_if_nessary()
        self._sync_dumped_index()

    def get_dumped_data_block_count(self):
        with self._lock:
            self._sync_dumped_index()
            return self._dumped_index + 1

    def get_data_block_meta_by_index(self, index):
        with self._lock:
            if index < 0:
                raise IndexError("{} index out of range".format(index))
            self._sync_dumped_index()
            return self._sync_data_block_meta(index)

    def get_lastest_data_block_meta(self):
        with self._lock:
            self._sync_dumped_index()
            return self._sync_data_block_meta(self._dumped_index)

    def commit_data_block_meta(self, tmp_meta_fpath, data_block_meta):
        if not gfile.Exists(tmp_meta_fpath):
            raise RuntimeError("the tmp file is not existed {}"\
                               .format(tmp_meta_fpath))
        with self._lock:
            if self._dumping_index is not None:
                raise RuntimeError(
                        "data block with index {} is " \
                        "dumping".format(self._dumping_index)
                    )
            data_block_index = data_block_meta.data_block_index
            if data_block_index != self._dumped_index + 1:
                raise IndexError("the data block index shoud be consecutive")
            self._dumping_index = data_block_index
            meta_fpath = self._get_data_block_meta_path(data_block_index)
            gfile.Rename(tmp_meta_fpath, meta_fpath)
            self._dumping_index = None
            self._dumped_index = data_block_index
            self._evict_data_block_cache_if_full()
            self._data_block_meta_cache[data_block_index] = data_block_meta

    def _sync_dumped_index(self):
        if self._dumped_index is None:
            assert self._dumping_index is None, \
                "no index is dumping when no dumped index"
            left_index = 0
            right_index = 1 << 63
            while left_index <= right_index:
                index = (left_index + right_index) // 2
                fname = self._get_data_block_meta_path(index)
                if gfile.Exists(fname):
                    left_index = index + 1
                else:
                    right_index = index - 1
            self._dumped_index = right_index
        elif self._dumping_index is not None:
            assert self._dumping_index == self._dumped_index + 1, \
                "the dumping index shoud be next of dumped index "\
                "{} != {} + 1".format(self._dumping_index, self._dumped_index)
            fpath = self._get_data_block_meta_path(self._dumping_index)
            if not gfile.Exists(fpath):
                self._dumping_index = None
            else:
                self._dumped_index = self._dumping_index
                self._dumping_index = None

    def _make_directory_if_nessary(self):
        data_block_dir = self._data_block_dir()
        if not gfile.Exists(data_block_dir):
            gfile.MakeDirs(data_block_dir)
        if not gfile.IsDirectory(data_block_dir):
            logging.fatal("%s should be directory", data_block_dir)
            os._exit(-1) # pylint: disable=protected-access

    def _sync_data_block_meta(self, index):
        if self._dumped_index < 0 or index > self._dumped_index:
            return None
        if index not in self._data_block_meta_cache:
            self._evict_data_block_cache_if_full()
            fpath = self._get_data_block_meta_path(index)
            meta = load_data_block_meta(fpath)
            if meta is None:
                logging.fatal("data block index as %d has dumped "\
                              "but vanish", index)
                os._exit(-1) # pylint: disable=protected-access
            self._data_block_meta_cache[index] = meta
        return self._data_block_meta_cache[index]

    def _get_data_block_meta_path(self, data_block_index):
        meta_fname = encode_data_block_meta_fname(
                self._data_source.data_source_meta.name,
                self._partition_id, data_block_index
            )
        return os.path.join(self._data_block_dir(), meta_fname)

    def _data_block_dir(self):
        return os.path.join(self._data_source.data_block_dir,
                            partition_repr(self._partition_id))

    def _evict_data_block_cache_if_full(self):
        while len(self._data_block_meta_cache) >= 1024:
            self._data_block_meta_cache.popitem()
