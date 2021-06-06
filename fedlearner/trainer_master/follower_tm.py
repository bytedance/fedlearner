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
from fedlearner.trainer.data_visitor import DataSourceVisitor


class FollowerTrainerMaster(object):
    def __init__(self, application_id, data_source):
        self._application_id = application_id
        self._data_visitor = DataSourceVisitor(data_source)

    def run(self, listen_port):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        tm_grpc.add_TrainerMasterServiceServicer_to_server(self)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Trainer Master Server start on port[%d].', listen_port)
        self._server.wait_for_termination()

    def RequestDataBlock(self, request, context):
        data_block = self._data_visitor.get_datablock_by_id(request.block_id)
        if data_block:
            logging.info("allocated worker_%d with block: %s",
                          request.worker_rank,
                          data_block.id)
            response = tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_SUCCESS),
                block_id=data_block.id,
                data_path=data_block.data_path,
            )
        else:
            logging.error("invalid data block id: %s", request.block_id)
            response = tm_pb.DataBlockResponse(
                status=common_pb.Status(
                    code=common_pb.StatusCode.STATUS_INVALID_DATA_BLOCK,
                    error_message="invalid data block")
                )
        return response

if __name__ == '__main__':
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
    parser.add_argument('--verbosity',
                        type=int,
                        default=1,
                        help='Logging level.')

    args = parser.parse_args()
    def _verbosity_to_loglevel(verbosity):
        if verbosity == 0:
            return logging.WARNING
        if verbosity == 1:
            return logging.INFO
        # other
        return logging.DEBUG
    logging.basicConfig(
        level=_verbosity_to_loglevel(args.verbosity),
        format="%(asctime)-15s [%(levelname)s]: %(message)s "
               "(%(filename)s:%(lineno)d)")

    follower_tm = FollowerTrainerMaster(
        args.application_id, args.data_source)
    follower_tm.run(listen_port=args.port)
