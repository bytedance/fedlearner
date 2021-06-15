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
import traceback
try:
    import tensorflow.compat.v1 as tf
except ImportError:
    import tensorflow.compat.v1 as tf

from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.common import common_pb2 as common_pb
from fedlearner.data_join.data_block_visitor import DataBlockVisitor

DataBlockInfo = collections.namedtuple('DataBlockInfo',
                                       ['block_id', 'data_path'])
kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')


class LocalTrainerMasterClient(object):
    """Non-thread safe"""
    def __init__(self,
                 role,
                 path,
                 files=None,
                 ext='.tfrecord',
                 start_time=None,
                 end_time=None,
                 from_data_source=False,
                 skip_datablock_checkpoint=False,
                 epoch_num=1):
        self._role = role
        self._path = path
        self._block_queue = []
        self._block_map = {}
        self._allocated_data_blockids = set()
        self._status = tm_pb.MasterStatus.CREATED
        if from_data_source:
            data_block_visitor = DataBlockVisitor(path, kvstore_type)
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

            # Hack way for supporting multiple epochs
            blocks = []
            for filename in files:
                block_id, _ = os.path.splitext(os.path.basename(filename))
                fullname = os.path.join(path, filename)
                block = DataBlockInfo(block_id, fullname)
                blocks.append(block)
            self._block_map = {block.block_id: block for block in blocks}
            for rnd in range(epoch_num):
                for block in blocks:
                    self._block_queue.append(block)

        self._status = tm_pb.MasterStatus.INITIALING
        if skip_datablock_checkpoint:
            self._status = tm_pb.MasterStatus.RUNNING

    def request_data_block(self, block_id=None):
        if self._status != tm_pb.MasterStatus.RUNNING:
            response = tm_pb.DataBlockResponse()
            response.status.code = \
                   common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
            response.status.error_message = \
                    "must sync data checkpoint before alloc"
            return response
        if self._role == 'leader':
            assert block_id is None, "Must not set block_id for leader"
            while self._block_queue:
                ret = self._block_queue.pop(0)
                logging.debug('Fetch data block %s, ckpt is %s', ret,
                              ",".join(self._allocated_data_blockids))
                self._allocated_data_blockids.add(ret.block_id)
                logging.info('Fetch data block %s done', ret)
                return ret
            return None

        assert block_id, "Must set block_id for follower"
        if block_id not in self._block_map:
            return None
        return self._block_map[block_id]

    def get_data_block_checkpoint(self, appid):
        if self._status != tm_pb.MasterStatus.RUNNING:
            logging.warning(
                "invalid status when "
                "getting data block ckpt %s", self._status)
            return []
        return list(self._allocated_data_blockids)

    def restore_data_block_checkpoint(self, appid, block_ids):
        if self._status != tm_pb.MasterStatus.INITIALING:
            logging.warning("invalid status when restoring data block ckpt")
            return False
        self._allocated_data_blockids |= set(block_ids)
        self._status = tm_pb.MasterStatus.RUNNING
        return True


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

    def get_data_block_checkpoint(self, appid):
        req = tm_pb.GetDataBlockCheckpointRequest()
        req.application_id = appid
        try:
            result = self._stub.GetDataBlockCheckpoint(req)
        except Exception as e:  # pylint: disable=broad-except
            logging.warning("Get data blocks checkpoint failed: %s", \
                           e.code().name)
            return []
        else:
            if result.status.code == common_pb.STATUS_SUCCESS:
                return result.block_ids
            logging.warning("Get data blocks checkpoint error, %d, %s", \
                           result.status.code,
                           result.status.error_message)
            return []

    def restore_data_block_checkpoint(self, appid, block_ids):
        req = tm_pb.RestoreDataBlockCheckpointRequest()
        req.application_id = appid
        req.block_ids.extend(block_ids)
        try:
            result = self._stub.RestoreDataBlockCheckpoint(req)
        except Exception as e:  # pylint: disable=broad-except
            traceback.print_exc()
            logging.warning("Restore data blocks checkpoint failed: %s", \
                           e.code().name)
            return False
        else:
            if result.status.code == common_pb.STATUS_SUCCESS:
                return True
            logging.warning("Restore data blocks checkpoint error, %d, %s", \
                           result.status.code,
                           result.status.error_message)
            return False

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
                    logging.debug("%s:%d succeeded to get data block %s at %s",
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
