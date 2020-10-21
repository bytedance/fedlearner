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
import threading
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
        self._checkpoint_mutex = threading.Lock()
        self._allocated_data_blockids = set()
        self._status_mutex = threading.Lock()
        self._status = tm_pb.MasterStatus.CREATED

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
        self._transfer_status(tm_pb.MasterStatus.CREATED,
                              tm_pb.MasterStatus.INITIALING)
        self._server.wait_for_termination()

    def _transfer_status(self, frm, to, callback_fn=lambda *args: True):
        with self._status_mutex:
            if self._status == frm:
                self._status = to
                return callback_fn()
            logging.error("%s invalid status transfer, from %d to %d, "
                          "when status is %d", self.__class__.__name__,
                          frm, to, self._status)
            self._status = tm_pb.MasterStatus.ERROR
        return False

    def _check_status(self, callback_fn):
        with self._status_mutex:
            return callback_fn(self._status)
        raise ValueError("unreachable")

    def _get_checkpoint_fn(self, request):
        assert request.application_id == self._application_id, \
                "Application id not matched"
        response = tm_pb.GetDataBlockCheckpointResponse()
        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = 'success'
        response.block_ids.extend(list(self._allocated_data_blockids))
        return response

    def _restore_checkpoint_fn(self, request):
        assert request.application_id == self._application_id,\
                "Application id not matched"
        response = tm_pb.RestoreDataBlockCheckpointResponse()

        trans_ok = self._transfer_status(tm_pb.MasterStatus.INITIALING,
                             tm_pb.MasterStatus.RUNNING)
        if not trans_ok:
            response.status.code = common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
            response.status.error_message = \
                    "must sync data checkpoint before alloc"
            return response
        with self._checkpoint_mutex:
            #reset the checkpoints only when the master restarted
            if len(self._allocated_data_blockids) == 0:
                self._allocated_data_blockids |= set(request.block_ids)
        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = "success"
        return response

    def _get_checkpoint(self):
        return self._allocated_data_blockids

    def _alloc_data_block(self, block_id=None):
        raise NotImplementedError("This method needs to be overridden")

    def _data_block_response(self, request):
        response = tm_pb.DataBlockResponse()
        def status_check_fn(status):
            response = tm_pb.DataBlockResponse()
            if status in (tm_pb.MasterStatus.FINISHED, \
                    tm_pb.MasterStatus.ERROR):
                response.status.code = common_pb.STATUS_DATA_FINISHED
                response.status.error_message = 'datablock finished'
                return response
            if status != tm_pb.MasterStatus.RUNNING:
                response.status.code = \
                       common_pb.STATUS_WAIT_FOR_SYNCING_CHECKPOINT
                response.status.error_message = \
                        "must sync data checkpoint before alloc"
                return response
            #only if status is RUNNING
            return True

        ready = self._check_status(status_check_fn)
        if ready is not True:
            return ready
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
        if response.status.code == common_pb.STATUS_DATA_FINISHED:
            self._transfer_status(tm_pb.MasterStatus.RUNNING,
                                 tm_pb.MasterStatus.FINISHED)
        return response

    def _load_data(self):
        raise NotImplementedError("This method needs to be overridden")
