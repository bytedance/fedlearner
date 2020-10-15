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

import enum
import logging
from concurrent import futures
import threading
import grpc
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import common_pb2 as common_pb
from .trainer_master_service import TrainerMasterServer

class MasterStatus(enum.Enum):
    CREATED = 0
    INITIALING = 1
    RUNNING = 2
    FINISHED = 3
    ERROR = 4

class TrainerMaster(object):
    def __init__(self, application_id, checkpoint_path=None,
                 online_training=False):
        self._application_id = application_id
        self._online_training = online_training
        self._checkpoint_mutex = threading.Lock()
        self._allocated_data_blockids = set()
        self._status_mutex = threading.Lock()
        self._status = MasterStatus.CREATED

    def run(self, listen_port):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        tm_grpc.add_TrainerMasterServiceServicer_to_server(
            TrainerMasterServer(self._data_block_response,
                                self._get_checkpoint_fn,
                                self._restore_checkpoint_fn), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Trainer Master Server start on port[%d].', listen_port)
        self._load_data()
        self._status = MasterStatus.INITIALING
        self._server.wait_for_termination()

    def _get_checkpoint_fn(self, request):
        assert request.application_id == self._application_id, \
                "application id not matched"
        response = tm_pb.GetDataBlockCheckpointResponse()
        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = 'success'
        response.block_ids.extend(list(self._allocated_data_blockids))
        return response

    def _restore_checkpoint_fn(self, request):
        assert request.application_id == self._application_id,\
                "application id not matched"
        with self._checkpoint_mutex:
            self._allocated_data_blockids |= set(request.block_ids)
        with self._status_mutex:
            if self._status != MasterStatus.INITIALING:
                logging.warning("master status is %s, which can not "
                                "transfer to RUNNING directly",
                               self._status.name)
            self._status = MasterStatus.RUNNING

    def _get_checkpoint(self):
        return self._allocated_data_blockids

    def _alloc_data_block(self, block_id=None):
        raise NotImplementedError("This method needs to be overridden")

    def _data_block_response(self, request):
        response = tm_pb.DataBlockResponse()
        with self._status_mutex:
            if self._status != MasterStatus.RUNNING:
                response.status.code = \
                        common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
                response.status.error_message = \
                        "wait for chief worker to sync checkpoint"
                return response
        data_block = self._alloc_data_block(block_id=request.block_id)
        if data_block:
            logging.debug("%s allocated worker_%d with block id %s",
                          self.__class__.__name__,
                          request.worker_rank,
                          data_block.block_id)
            response.status.code = common_pb.STATUS_SUCCESS
            response.status.error_message = 'success'
            response.data_block_info.data_path = \
                str(data_block.data_block_fpath)
            response.data_block_info.meta_path = ''
            response.data_block_info.block_id = str(data_block.block_id)
        elif self._online_training:
            logging.debug("%s allocated worker_%d with empty data block. "\
                          "wait for new data block since online traning",
                          self.__class__.__name__, request.worker_rank)
            response.status.code = common_pb.STATUS_NO_MORE_DATA
            response.status.error_message = 'please wait for datablock ready'
        else:
            logging.debug("%s allocated worker_%d with empty data block. "\
                          "exit running since since batch traning",
                          self.__class__.__name__, request.worker_rank)
            response.status.code = common_pb.STATUS_DATA_FINISHED
            response.status.error_message = 'datablock finished'
            self._status = MasterStatus.FINISHED
        return response

    def _load_data(self):
        raise NotImplementedError("This method needs to be overridden")
