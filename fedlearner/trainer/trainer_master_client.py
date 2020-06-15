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
import time
import logging
import collections
import tensorflow.compat.v1 as tf

from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.common import common_pb2 as common_pb
from fedlearner.data_join.data_block_visitor import DataBlockVisitor

DataBlockInfo = collections.namedtuple('DataBlockInfo',
                                       ['block_id', 'data_path'])
ETCD_NAME = os.environ.get('ETCD_NAME', None)
ETCD_ADDR = os.environ.get('ETCD_ADDR', None)
ETCD_BASE_DIR = os.environ.get('ETCD_BASE_DIR', None)


class LocalTrainerMasterClient(object):
    def __init__(self,
                 role,
                 path,
                 files=None,
                 ext='.tfrecord',
                 start_time=None,
                 end_time=None,
                 from_data_source=False):
        self._role = role
        self._path = path
        self._block_queue = []
        self._block_map = {}
        if from_data_source:
            data_block_visitor = DataBlockVisitor(path, ETCD_NAME,
                                                  ETCD_BASE_DIR, ETCD_ADDR)
            # pylint: disable=line-too-long
            for block_id, block_item in data_block_visitor.LoadDataBlockRepByTimeFrame(
                    start_time, end_time).items():
                self._block_queue.append(block_item)
                self._block_map[block_id] = block_item
        else:
            if files is None:
                files = []
                for dirname, _, filenames in tf.io.gfile.walk(path):
                    for filename in filenames:
                        _, fileext = os.path.splitext(filename)
                        if ext and fileext != ext:
                            continue
                        subdirname = os.path.relpath(dirname, path)
                        files.append(os.path.join(subdirname, filename))
            files.sort()

            block_map = {}
            for filename in files:
                block_id, _ = os.path.splitext(os.path.basename(filename))
                assert block_id not in block_map, \
                    "Duplicate file names: %s and %s"%(
                        filename, block_map[block_id])
                block_map[block_id] = filename
                fullname = os.path.join(path, filename)
                block = DataBlockInfo(block_id, fullname)
                self._block_queue.append(block)
                self._block_map[block_id] = block

    def request_data_block(self, block_id=None):
        if self._role == 'leader':
            assert block_id is None, "Must not set block_id for leader"
            if self._block_queue:
                ret = self._block_queue.pop(0)
                logging.debug('Return data block %s', ret)
                return ret
            return None

        assert block_id, "Must set block_id for follower"
        if block_id not in self._block_map:
            return None
        return self._block_map[block_id]


class TrainerMasterClient(object):
    def __init__(self, addr, role, task_id):
        self._addr = addr
        self._role = role
        self._task_id = task_id

        channel = make_insecure_channel(self._addr, ChannelType.INTERNAL)
        self._stub = tm_grpc.TrainerMasterServiceStub(channel)
        self._request = tm_pb.DataBlockRequest()
        if self._role == 'leader':
            self._request.worker_rank = self._task_id

    def request_data_block(self, block_id=None):
        if self._role == 'follower':
            assert block_id, "Must set block_id for follower"
            self._request.block_id = block_id

        while True:
            try:
                result = self._stub.RequestDataBlock(self._request)
            except Exception as e:  # pylint: disable=broad-except
                logging.warning("Get data block failed: %s. " \
                                    "Retry in 1 second...",
                                e.code().name)
            else:
                if result.status.code == common_pb.STATUS_SUCCESS:
                    logging.debug("%s:%d failed to get data block %s at %s",
                                  self._role, self._task_id,
                                  result.data_block_info.block_id,
                                  result.data_block_info.data_path)
                    return DataBlockInfo(result.data_block_info.block_id,
                                         result.data_block_info.data_path)
                if result.status.code == common_pb.STATUS_DATA_FINISHED:
                    logging.warning("%s:%d gets block allocated finished.",
                                    self._role, self._task_id)
                    break
                logging.warning("%s:%d failed to get data block %s at %s"\
                                "code: %d, message: %s. Retry in 1 second...",
                                self._role, self._task_id,
                                result.data_block_info.block_id,
                                result.data_block_info.data_path,
                                result.status.code,
                                result.status.error_message)
            time.sleep(1)
        return None
