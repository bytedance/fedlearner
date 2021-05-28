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
import threading
import collections
import random
import sys
from datetime import timedelta, datetime

import tensorflow.compat.v1 as tf
from fedlearner.common import fl_logging
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.data_join.data_block_visitor import DataBlockVisitor


kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')
kvstore_use_mock = os.environ.get('KVSTORE_USE_MOCK', "off") == "on"


class _RawDataBlock(
    collections.namedtuple('RowDataBlock',
                           ['id', 'data_path', 'start_time', 'end_time',
                            'type'])):
    pass


class DataBlock(
    collections.namedtuple('DataBlock',
                           ['id', 'epoch', 'data_path', 'type'])):
    pass


class ShuffleType(object):
    ALL = 'all'
    DAY = 'day'


class RawDataBlockDealer(object):
    def __init__(self, data_blocks):
        self._data_blocks = data_blocks

    @property
    def data_blocks(self):
        return self._data_blocks

    def time_translate(self, forward, day, hour=0,):
        delta = timedelta(days=day, hours=hour)
        date_fmt = '%Y%m%d'
        for db in self._data_blocks:
            start_time = db.start_time[:8]
            end_time = db.end_time[:8]
            if forward:
                new_start_time = datetime.strptime(start_time, date_fmt) + delta
                new_end_time = datetime.strptime(end_time, date_fmt) + delta
            else:
                new_start_time = datetime.strptime(start_time, date_fmt) - delta
                new_end_time = datetime.strptime(end_time, date_fmt) - delta
            db.start_time = new_start_time.strftime(date_fmt) + start_time[8:]
            db.end_time = new_end_time.strftime(date_fmt) + end_time[8:]
        return self

    def merge_data_blocks(self, data_blocks):
        self._data_blocks.extend(data_blocks)
        return self

    def shuffle(self):
        random.shuffle(self._data_blocks)
        return self

    def shuffle_in_day(self):
        def _shuffle(_start_index, _end_index):
            # using Fisher–Yates shuffle Algorithm
            for i in range(_end_index, _start_index, -1):
                j = random.randint(_start_index, i)
                self._data_blocks[i], self._data_blocks[j] = \
                    self._data_blocks[j], self._data_blocks[i]

        start_index = 0
        end_index = 1
        num_data_blocks = len(self._data_blocks)
        if not self._data_blocks or not self._data_blocks[0].start_time:
            return
        start_day = self._data_blocks[0].start_time[:8]
        while end_index < num_data_blocks:
            new_day = self._data_blocks[end_index].start_time[:8]
            if new_day != start_day:
                _shuffle(start_index, end_index-1)
                start_index = end_index
                start_day = new_day
            end_index += 1
        _shuffle(start_index, end_index - 1)
        return self


class _DataVisitor(object):
    def __init__(self, datablocks, epoch_num=1,
                 shuffle_type=None):
        self._datablocks = list(datablocks)
        self._datablock_dict = {}
        for datablock in datablocks:
            fl_logging.info("load datablock, id: %s, data_path: %s, type %s",
                            datablock.id, datablock.data_path, datablock.type)
            self._datablock_dict[datablock.id] = datablock
        self._epoch_num = epoch_num if epoch_num > 0 else 1
        self._shuffle_type = shuffle_type

        self._lock = threading.Lock()
        self._datablock_index = 0
        self._current_epoch = 1
        self._allocated = {} # epoch -> set(datablock.id)

        self._shuffle_data_blocks()

    @property
    def epoch_num(self):
        return self._epoch_num

    @property
    def datablock_size(self):
        return len(self._datablocks) * self._epoch_num

    def _shuffle_data_blocks(self):
        dealer = RawDataBlockDealer(self._datablocks)
        if self._shuffle_type == ShuffleType.ALL:
            dealer.shuffle()
        elif self._shuffle_type == ShuffleType.DAY:
            dealer.shuffle_in_day()
        elif self._shuffle_type:
            fl_logging.fatal("Not supported shuffle type %s",
                             self._shuffle_type)
            sys.exit(-1)

    def summary(self):
        with self._lock:
            return (self._current_epoch,
                    (self._current_epoch-1) * len(self._datablocks) \
                        + self._datablock_index)

    def dump(self):
        with self._lock:
            data = {
                "checkpoints": {}
            }
            for epoch in self._allocated:
                key = "epoch-" + str(epoch)
                data["checkpoints"][key] = sorted(self._allocated[epoch])
        return zlib.compress(json.dumps(data).encode())

    def restore(self, buff):
        data = self._try_parse_v2(buff)
        if not data:
            data = self._try_parse_v1(buff)
        if not data:
            return

        with self._lock:
            for key in data["checkpoints"]:
                if not key.startswith("epoch-"):
                    continue
                epoch = int(key[6:])
                if epoch not in self._allocated:
                    self._allocated[epoch] = set()
                for block_id in data["checkpoints"][key]:
                    fl_logging.info("LeaderDataVisitor restore datablock, "
                                    "epoch: %d, block_id: %s", epoch, block_id)
                    self._allocated[epoch].add(block_id)
            try:
                self._next(peek=True)
            except Exception:
                pass

    def get_datablock_by_id(self, block_id, epoch=1):
        if block_id not in self._datablock_dict:
            return None
        datablock = self._datablock_dict[block_id]
        return DataBlock(datablock.id, epoch, datablock.data_path,
                         datablock.type)

    def _try_parse_v2(self, buff):
        try:
            data = json.loads(zlib.decompress(buff))
            assert "checkpoints" in data
            return data
        except Exception:
            pass

    def _try_parse_v1(self, buff):
        try:
            return {
                "checkpoints": {
                    "epoch-1": buff.split(",")
                }
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
                                     datablock.data_path,
                                     datablock.type)
                self._datablock_index += 1

            if self._current_epoch == self._epoch_num:
                raise StopIteration()

            self._current_epoch += 1
            self._datablock_index = 0
            self._shuffle_data_blocks()

    def next_with_type(self, data_block_type):
        with self._lock:
            data_block = self._next(peek=True)
            if data_block.type == data_block_type:
                return self._next()
            else:
                return None

    def __next__(self):
        with self._lock:
            return self._next()

    next = __next__


class DataSourceVisitor(_DataVisitor):
    def __init__(self,
                 data_source,
                 start_date=None,
                 end_date=None,
                 local_data_source=None,
                 local_start_date=None,
                 local_end_date=None,
                 epoch_num=1,
                 shuffle_type=None):
        fl_logging.info("Load data_source: %s", data_source)
        data_block_visitor = DataBlockVisitor(
            data_source, kvstore_type, kvstore_use_mock)
        data_blocks = []
        for datablock in data_block_visitor.LoadDataBlockRepByTimeFrame(
            start_date, end_date).values():
            data_blocks.append(
                _RawDataBlock(datablock.block_id, datablock.data_block_fpath,
                              datablock.start_time, datablock.end_time,
                              tm_pb.JOINED))
        if local_data_source:
            fl_logging.info("Load local data_source: %s", local_data_source)
            data_block_visitor = DataBlockVisitor(
                local_data_source, kvstore_type, kvstore_use_mock)
            for datablock in data_block_visitor.LoadDataBlockRepByTimeFrame(
                    local_start_date, local_end_date).values():
                data_blocks.append(
                    _RawDataBlock(datablock.block_id,
                                  datablock.data_block_fpath,
                                  datablock.start_time,
                                  datablock.end_time,
                                  tm_pb.LOCAL))
        data_blocks.sort(key=lambda x: (x.start_time, x.end_time))

        super(DataSourceVisitor, self).__init__(
            data_blocks, epoch_num, shuffle_type)


class DataPathVisitor(_DataVisitor):
    def __init__(self,
                 data_path,
                 ext=".tfrecord",
                 epoch_num=1,
                 shuffle_type=None):
        fl_logging.info("create DataVisitor by data_path: %s", data_path)
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
                datablock = _RawDataBlock(block_id,
                                          os.path.join(dirname, filename),
                                          None, None,
                                          tm_pb.JOINED)
                datablocks.append(datablock)
        datablocks.sort()

        super(DataPathVisitor, self).__init__(datablocks, epoch_num,
                                              shuffle_type)
