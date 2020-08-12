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
from concurrent import futures
import grpc
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import common_pb2 as common_pb
from .trainer_master_service import TrainerMasterServer


class TrainerMaster(object):
    def __init__(self, application_id, checkpoint_path=None,
                 online_training=False):
        self._application_id = application_id
        self._online_training = online_training

    def run(self, listen_port):
        # TrainerMaster need to load data_block from store or disk at first.
        # if TrainerMaster shutdown, need to recovery from previous checkpoint.
        self._load_data()
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        tm_grpc.add_TrainerMasterServiceServicer_to_server(
            TrainerMasterServer(self._data_block_response), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Trainer Master Server start on port[%d].', listen_port)
        self._server.wait_for_termination()

    def _get_checkpoint(self):
        # TODO need to checkpoint the data alloc record.
        return set()

    def _alloc_data_block(self, block_id=None):
        raise NotImplementedError("This method needs to be overridden")

    def _data_block_response(self, request):
        data_block = self._alloc_data_block(block_id=request.block_id)
        response = tm_pb.DataBlockResponse()
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
        return response

    def _load_data(self):
        raise NotImplementedError("This method needs to be overridden")
