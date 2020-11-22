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

import sys
import traceback

from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import common_pb2 as common_pb


class TrainerMasterServer(tm_grpc.TrainerMasterServiceServicer):
    def __init__(self, receiver_fn, get_checkpoint_fn, restore_fn):
        super(TrainerMasterServer, self).__init__()
        self._receiver_fn = receiver_fn
        self._get_checkpoint_fn = get_checkpoint_fn
        self._restore_checkpoint_fn = restore_fn

    def GetDataBlockCheckpoint(self, request, context):
        response = tm_pb.GetDataBlockCheckpointResponse()
        try:
            response = self._get_checkpoint_fn(request)
        except Exception:  # pylint: disable=broad-except
            response.status.code = common_pb.STATUS_UNKNOWN_ERROR
            err_str = ''.join(traceback.format_exception(*sys.exc_info()))
            response.status.error_message = err_str
        return response

    def RestoreDataBlockCheckpoint(self, request, context):
        response = tm_pb.RestoreDataBlockCheckpointResponse()
        try:
            response = self._restore_checkpoint_fn(request)
        except Exception:  # pylint: disable=broad-except
            response.status.code = common_pb.STATUS_UNKNOWN_ERROR
            err_str = ''.join(traceback.format_exception(*sys.exc_info()))
            response.status.error_message = err_str
        return response

    def RequestDataBlock(self, request, context):
        response = tm_pb.DataBlockResponse()
        try:
            response = self._receiver_fn(request)
        except Exception:  # pylint: disable=broad-except
            response.status.code = common_pb.STATUS_UNKNOWN_ERROR
            err_str = ''.join(traceback.format_exception(*sys.exc_info()))
            response.status.error_message = err_str
        return response
