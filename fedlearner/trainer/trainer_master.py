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

import collections
import logging
import os

from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.common import common_pb2 as common_pb

DataBlockInfo = collections.namedtuple('DataBlockInfo',
                                       ['block_id', 'data_path'])


class LocalTrainerMasterClient(object):
    def __init__(self, role, path, files=None, ext='.tfrecord'):
        self._role = role
        self._path = path
        if files is None:
            files = []
            for filename in os.listdir(path):
                fullname = os.path.join(path, filename)
                if not os.path.isfile(fullname):
                    continue
                _, fileext = os.path.splitext(filename)
                if ext and fileext != ext:
                    continue
                files.append(filename)
        files.sort()
        self._block_queue = []
        self._block_map = {}
        for filename in files:
            block_id, _ = os.path.splitext(filename)
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

        result = self._stub.RequestDataBlock(self._request)
        if result.status.code == common_pb.STATUS_SUCCESS:
            logging.debug("%d:%d gets block %s at %s", self._role,
                          self._task_id, result.data_block_info.block_id,
                          result.data_block_info.data_path)
            return DataBlockInfo(result.data_block_info.block_id,
                                 result.data_block_info.data_path)

        logging.error("%s:%d gets block failed with error[%s].", self._role,
                      self._task_id, result.status.error_message)
        return None
