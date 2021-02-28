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

import argparse
import logging
import os
from concurrent import futures
import grpc

from fedlearner.data_join.data_block_visitor import DataBlockVisitor
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import common_pb2 as common_pb

from .trainer_master_service import TrainerMasterServer

kvstore_type = os.environ.get('KVSTORE_TYPE', 'etcd')

class FollowerTrainerMaster(object):
    def __init__(self, application_id, data_source, online_training):
        self._application_id = application_id
        self._online_training = online_training
        kvstore_use_mock = os.environ.get('KVSTORE_USE_MOCK', "off") == "on"
        self._data_block_visitor = DataBlockVisitor(
            data_source, kvstore_type, kvstore_use_mock)

    def run(self, listen_port):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        tm_grpc.add_TrainerMasterServiceServicer_to_server(
            TrainerMasterServer(self._data_block_response,
                                self._get_checkpoint_fn,
                                self._restore_checkpoint_fn), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Trainer Master Server start on port[%d].', listen_port)
        self._server.wait_for_termination()

    def _get_checkpoint_fn(self, request):
        response = tm_pb.GetDataBlockCheckpointResponse()
        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = 'success'
        logging.info("Follower _get_checkpoint_fn, do nothing")
        return response

    def _restore_checkpoint_fn(self, request):
        response = tm_pb.RestoreDataBlockCheckpointResponse()
        response.status.code = common_pb.STATUS_SUCCESS
        response.status.error_message = "success"
        logging.info("Follower _restore_checkpoint_fn, do nothing")
        return response

    def _alloc_data_block(self, block_id=None):
        logging.info("FollowerTrainerMaster is getting block %s", block_id)
        if not block_id:
            raise Exception('follower tm need block_id to alloc.')
        return self._data_block_visitor.LoadDataBlockRepByBlockId(block_id)

    def _data_block_response(self, request):
        response = tm_pb.DataBlockResponse()
        data_block = self._alloc_data_block(block_id=request.block_id)
        if data_block:
            logging.info("%s allocated worker_%d with block id %s",
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
            logging.info("%s allocated worker_%d with empty data block. "\
                          "wait for new data block since online traning",
                          self.__class__.__name__, request.worker_rank)
            response.status.code = common_pb.STATUS_NO_MORE_DATA
            response.status.error_message = 'please wait for datablock ready'
        else:
            logging.info("%s allocated worker_%d with empty data block. "\
                          "exit running since since batch traning",
                          self.__class__.__name__, request.worker_rank)
            response.status.code = common_pb.STATUS_DATA_FINISHED
            response.status.error_message = 'datablock finished'
        return response

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser('follower trainer master cmd.')
    parser.add_argument('-p',
                        '--port',
                        type=int,
                        default=50002,
                        help='Listen port of follower trainer master')
    parser.add_argument('-app_id',
                        '--application_id',
                        required=True,
                        help='application_id')
    parser.add_argument('-data_source',
                        '--data_source',
                        required=True,
                        help='training example data source')
    # FIXME: deprecated
    parser.add_argument('-start_date',
                        '--start_date',
                        default=None,
                        help='training data start date')
    # FIXME: deprecated
    parser.add_argument('-end_date',
                        '--end_date',
                        default=None,
                        help='training data end date')
    parser.add_argument('--online_training',
                        action='store_true',
                        help='the train master run for online training')

    FLAGS = parser.parse_args()
    start_date = int(FLAGS.start_date) if FLAGS.start_date else None
    end_date = int(FLAGS.end_date) if FLAGS.end_date else None
    follower_tm = FollowerTrainerMaster(
        FLAGS.application_id, FLAGS.data_source,
        FLAGS.online_training)
    follower_tm.run(listen_port=FLAGS.port)
