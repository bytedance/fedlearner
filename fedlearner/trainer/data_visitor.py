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
# pylint: disable=broad-except

import os
import zlib
import json
import logging
import threading
import collections
import random

import tensorflow.compat.v1 as tf
from fedlearner.data_join.data_block_visitor import DataBlockVisitor
from fedlearner.common import trainer_master_service_pb2 as tm_pb


kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')
kvstore_use_mock = os.environ.get('KVSTORE_USE_MOCK', "off") == "on"


class _RowDataBlock(
    collections.namedtuple('RowDataBlock',
                           ['id', 'data_path'])):
    pass


class DataBlock(
    collections.namedtuple('DataBlock',
                           ['id', 'epoch', 'data_path'])):
    pass


class _DataVisitor(object):
    def __init__(self, datablocks, epoch_num=1, shuffle=False):
        self._datablocks = list(datablocks)
        self._datablock_dict = {}
        for datablock in datablocks:
            logging.info("load datablock, id: %s, data_path: %s",
                         datablock.id, datablock.data_path)
            self._datablock_dict[datablock.id] = datablock
        self._epoch_num = epoch_num if epoch_num > 0 else -1
        self._shuffle = shuffle

        self._lock = threading.Lock()
        self._datablock_index = 0
        self._current_epoch = 1
        self._allocated = {} # epoch -> set(datablock.id)

        self._checkpoints_key = "checkpoints"
        self._epoch_key_prefix = "epoch-"
        self._datablock_index_key = "datablock_index"

        if self._shuffle:
            random.shuffle(self._datablocks)

    @property
    def epoch_num(self):
        return self._epoch_num

    @property
    def datablock_size(self):
        return len(self._datablocks)

    def summary(self):
        with self._lock:
            return (self._current_epoch,
                    (self._current_epoch-1) * len(self._datablocks) \
                        + self._datablock_index)

    def dump(self):
        with self._lock:
            data = {
                self._checkpoints_key: {},
                self._datablock_index_key: self._datablock_index
            }
            for epoch in self._allocated:
                key = self._epoch_key_prefix + str(epoch)
                data[self._checkpoints_key][key] = \
                    sorted(self._allocated[epoch])
        return zlib.compress(json.dumps(data).encode())

    def restore(self, buff):
        data = self._try_parse_v2(buff)
        if not data:
            data = self._try_parse_v1(buff)
        if not data:
            return

        with self._lock:
            for key in data[self._checkpoints_key]:
                if not key.startswith(self._epoch_key_prefix):
                    continue
                epoch = int(key[6:])
                if epoch not in self._allocated:
                    self._allocated[epoch] = set()
                for block_id in data[self._checkpoints_key][key]:
                    logging.info("LeaderDataVisitor restore datablock, "
                                 "epoch: %d, block_id: %s", epoch, block_id)
                    self._allocated[epoch].add(block_id)
            self._datablock_index = data[self._datablock_index_key]
            try:
                self._next(peek=True)
            except Exception:
                pass

    def get_datablock_by_id(self, block_id, epoch=1):
        if block_id not in self._datablock_dict:
            return None
        datablock = self._datablock_dict[block_id]
        return DataBlock(datablock.id, epoch, datablock.data_path)

    def _try_parse_v2(self, buff):
        try:
            data = json.loads(zlib.decompress(buff))
            assert self._checkpoints_key in data
            return data
        except Exception:
            pass

    def _try_parse_v1(self, buff):
        try:
            return {
                self._checkpoints_key: {
                    self._epoch_key_prefix + "-1": buff.split(",")
                },
                self._datablock_index_key: 0
            }
        except Exception:
            pass

    def _check_allocated(self, epoch, datablock):
        if epoch not in self._allocated:
            return True
        return datablock.id not in self._allocated[epoch]

    def _allocate(self, epoch, datablock):
        if epoch not in self._allocated:
            self._allocated[epoch] = set()
        self._allocated[epoch].add(datablock.id)

    def _next(self, peek=False):
        while True:
            while self._datablock_index < len(self._datablocks):
                datablock = self._datablocks[self._datablock_index]
                if self._check_allocated(self._current_epoch, datablock):
                    if not peek:
                        self._datablock_index += 1
                        self._allocate(self._current_epoch, datablock)
                    return DataBlock(datablock.id,
                                     self._current_epoch,
                                     datablock.data_path)
                self._datablock_index += 1

            if self._current_epoch == self._epoch_num:
                raise StopIteration()

            self._current_epoch += 1
            self._datablock_index = 0
            if self._shuffle:
                random.shuffle(self._datablocks)

    def __next__(self):
        with self._lock:
            return self._next()

    next = __next__


class DataSourceVisitor(_DataVisitor):
    def __init__(self,
                 data_source,
                 data_source_type=tm_pb.JOINED,
                 start_date=None,
                 end_date=None,
                 epoch_num=1,
                 shuffle=False):
        logging.info("create DataVisitor by data_source: %s", data_source)
        self._data_source_type = data_source_type
        self._data_block_visitor = DataBlockVisitor(
            data_source, kvstore_type, kvstore_use_mock)
        datablocks = []
        for datablock in self._data_block_visitor.LoadDataBlockRepByTimeFrame(
            start_date, end_date).values():
            datablocks.append(datablock)
        datablocks.sort(key=lambda x: x.start_time)

        super(DataSourceVisitor, self).__init__(
            [_RowDataBlock(d.block_id, d.data_block_fpath) for d in datablocks],
            epoch_num,
            shuffle)


class DataPathVisitor(_DataVisitor):
    def __init__(self,
                 data_path,
                 ext=".tfrecord",
                 epoch_num=1,
                 shuffle=False):
        logging.info("create DataVisitor by data_path: %s", data_path)
        if not tf.io.gfile.exists(data_path):
            raise ValueError("data_path not found: %s"%data_path)

        datablocks = []
        for dirname, _, filenames in tf.io.gfile.walk(data_path):
            for filename in filenames:
                _, fileext = os.path.splitext(filename)
                if ext and fileext != ext:
                    continue
                subdirname = os.path.relpath(dirname, data_path)
                block_id = os.path.join(subdirname, filename)
                datablock = _RowDataBlock(block_id,
                                          os.path.join(dirname, filename))
                datablocks.append(datablock)
        datablocks.sort()

        super(DataPathVisitor, self).__init__(datablocks, epoch_num, shuffle)
