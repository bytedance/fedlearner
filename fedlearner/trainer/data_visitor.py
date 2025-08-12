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

from fnmatch import fnmatch
import os
import zlib
import json
import threading
import collections
import random
import sys
from datetime import timedelta, datetime
from typing import Optional

import tensorflow.compat.v1 as tf
from fedlearner.common import fl_logging
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common.common import convert_time_string_to_datetime
from fedlearner.common.common import end_with_valid_date
from fedlearner.common.common import get_process_dates
from fedlearner.data_join.data_block_visitor import DataBlockVisitor
from fedlearner.trainer.utils import match_date


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
            start_time = str(db.start_time)[:8]
            end_time = str(db.end_time)[:8]
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
        if not self._data_blocks or not self._data_blocks[0].end_time:
            return self
        start_day = str(self._data_blocks[0].end_time)[:8]
        while end_index < num_data_blocks:
            new_day = str(self._data_blocks[end_index].end_time)[:8]
            if new_day != start_day:
                _shuffle(start_index, end_index-1)
                start_index = end_index
                start_day = new_day
            end_index += 1
        _shuffle(start_index, end_index - 1)
        return self


class _DataVisitor(object):
    def __init__(self, datablocks, local_datablocks=None, epoch_num=1,
                 shuffle_type: Optional[ShuffleType] = None):
        self._datablocks = {
            tm_pb.JOINED: list(datablocks),
        }
        self._datablock_dict = {}
        for datablock in datablocks:
            self._datablock_dict[datablock.id] = datablock
        if local_datablocks:
            self._datablocks[tm_pb.LOCAL] = list(local_datablocks)
            for datablock in local_datablocks:
                self._datablock_dict[datablock.id] = datablock
        self._epoch_num = epoch_num if epoch_num > 0 else 1
        self._shuffle_type = shuffle_type

        self._lock = threading.Lock()
        self._datablock_index = {
            tm_pb.JOINED: 0,
            tm_pb.LOCAL: 0
        }

        self._current_epoch = 1
        self._allocated = {} # epoch -> set(datablock.id)

        self._shuffle_data_blocks()
        for datablock in self._datablocks[tm_pb.JOINED]:
            fl_logging.info("load data block, id: %s, data_path: %s, type %s",
                            datablock.id, datablock.data_path, datablock.type)
        if local_datablocks:
            for datablock in self._datablocks[tm_pb.LOCAL]:
                fl_logging.info("load data block, id: %s, data_path: %s, "
                                "type %s",
                                datablock.id, datablock.data_path,
                                datablock.type)

    @property
    def epoch_num(self):
        return self._epoch_num

    @property
    def datablock_size(self):
        return len(self._datablocks[tm_pb.JOINED]) * self._epoch_num

    @property
    def local_datablock_size(self):
        if tm_pb.LOCAL in self._datablocks:
            return len(self._datablocks[tm_pb.LOCAL]) * self._epoch_num
        return 0

    def _shuffle_data_blocks(self):
        for datablocks in self._datablocks.values():
            dealer = RawDataBlockDealer(datablocks)
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
            local_allocated_blocks = 0
            if tm_pb.LOCAL in self._datablocks:
                local_allocated_blocks = (self._current_epoch - 1) * \
                                         len(self._datablocks[tm_pb.LOCAL]) \
                                         + self._datablock_index[tm_pb.LOCAL]
            return (self._current_epoch,
                    (self._current_epoch-1) *
                    len(self._datablocks[tm_pb.JOINED]) \
                        + self._datablock_index[tm_pb.JOINED],
                    local_allocated_blocks)

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

    def _next(self, peek=False, data_type=tm_pb.JOINED):
        while True:
            while self._datablock_index[data_type] < \
                    len(self._datablocks[data_type]):
                datablock = self._datablocks[data_type][
                    self._datablock_index[data_type]]
                if self._check_allocated(self._current_epoch, datablock):
                    if not peek:
                        self._datablock_index[data_type] += 1
                        self._allocate(self._current_epoch, datablock)
                    return DataBlock(datablock.id,
                                     self._current_epoch,
                                     datablock.data_path,
                                     datablock.type)
                self._datablock_index[data_type] += 1

            if self._current_epoch == self._epoch_num:
                raise StopIteration()

            self._current_epoch += 1
            self._datablock_index = {
                tm_pb.JOINED: 0,
                tm_pb.LOCAL: 0
            }
            self._shuffle_data_blocks()

    def next_with_type(self, data_block_type):
        with self._lock:
            return self._next(data_type=data_block_type)

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
        local_data_blocks = []
        if local_data_source:
            fl_logging.info("Load local data_source: %s", local_data_source)
            data_block_visitor = DataBlockVisitor(
                local_data_source, kvstore_type, kvstore_use_mock)
            for datablock in data_block_visitor.LoadDataBlockRepByTimeFrame(
                    local_start_date, local_end_date).values():
                local_data_blocks.append(
                    _RawDataBlock(datablock.block_id,
                                  datablock.data_block_fpath,
                                  datablock.start_time,
                                  datablock.end_time,
                                  tm_pb.LOCAL))
        data_blocks.sort(key=lambda x: x.end_time)
        local_data_blocks.sort(key=lambda x: x.end_time)

        super(DataSourceVisitor, self).__init__(
            data_blocks, local_data_blocks, epoch_num, shuffle_type)


class DataPathVisitor(_DataVisitor):
    def __init__(self,
                 data_path: str,
                 local_data_path: str,
                 wildcard: str,
                 epoch_num: int = 1,
                 shuffle_type=None,
                 start_date=None,
                 end_date=None):
        fl_logging.info("create DataVisitor by data_path: %s", data_path)
        if not tf.io.gfile.exists(data_path):
            raise ValueError("data_path not found: %s"%data_path)

        if start_date:
            start_date = convert_time_string_to_datetime(str(start_date))
        if end_date:
            end_date = convert_time_string_to_datetime(str(end_date))
        datablocks = []
        if start_date and not end_with_valid_date(data_path):
            process_dates = get_process_dates(start_date, end_date)
            miss_dates = []
            for process_date in process_dates:
                dir_path = os.path.join(data_path, process_date)
                if not tf.io.gfile.exists(dir_path):
                    miss_dates.append(process_date)
                    continue
                for _, _, filenames in tf.io.gfile.walk(dir_path):
                    for filename in filenames:
                        if not fnmatch(os.path.join(dir_path, filename), wildcard):
                            continue
                        block_id = os.path.join(process_date, filename)
                        datablock = _RawDataBlock(
                            id=block_id, data_path=os.path.join(dir_path, filename),
                            start_time=None, end_time=None, type=tm_pb.JOINED)
                        datablocks.append(datablock)
            fl_logging.info('miss_dates: [%s]', ",".join(miss_dates))
        else:
            for dirname, _, filenames in tf.io.gfile.walk(data_path):
                for filename in filenames:
                    if not fnmatch(os.path.join(dirname, filename), wildcard):
                        continue
                    subdirname = os.path.relpath(dirname, data_path)
                    try:
                        cur_date = datetime.strptime(subdirname, '%Y%m%d')
                        if not match_date(cur_date, start_date, end_date):
                            continue
                    except Exception:
                        fl_logging.info('subdirname is not the format of time')
                    block_id = os.path.join(subdirname, filename)
                    datablock = _RawDataBlock(
                        id=block_id, data_path=os.path.join(dirname, filename),
                        start_time=None, end_time=None, type=tm_pb.JOINED)
                    datablocks.append(datablock)
        datablocks.sort(key=lambda x: x.id)

        fl_logging.info("create DataVisitor by local_data_path: %s",
                        local_data_path)
        local_datablocks = []
        if local_data_path and tf.io.gfile.exists(local_data_path):
            for dirname, _, filenames in tf.io.gfile.walk(local_data_path):
                for filename in filenames:
                    if not fnmatch(os.path.join(dirname, filename), wildcard):
                        continue
                    subdirname = os.path.relpath(dirname, local_data_path)
                    block_id = os.path.join(subdirname, filename)
                    datablock = _RawDataBlock(
                        id=block_id, data_path=os.path.join(dirname, filename),
                        start_time=None, end_time=None, type=tm_pb.LOCAL)
                    local_datablocks.append(datablock)
        local_datablocks.sort(key=lambda x: x.id)

        super(DataPathVisitor, self).__init__(datablocks, local_datablocks,
                                              epoch_num, shuffle_type)

    def _check_allocated(self, epoch: int, datablock: _RawDataBlock):
        if epoch not in self._allocated:
            return True
        return datablock.data_path not in self._allocated[epoch]

    def _allocate(self, epoch: int, datablock: _RawDataBlock):
        if epoch not in self._allocated:
            self._allocated[epoch] = set()
        self._allocated[epoch].add(datablock.data_path)
