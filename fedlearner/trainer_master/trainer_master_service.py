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

from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.common import trainer_master_service_pb2_grpc as tm_grpc
from fedlearner.common import common_pb2 as common_pb


class TrainerMasterServer(tm_grpc.TrainerMasterServiceServicer):
    def __init__(self, receiver_fn):
        super(TrainerMasterServer, self).__init__()
        self._receiver_fn = receiver_fn

    def RequestDataBlock(self, request, context):
        response = tm_pb.DataBlockResponse()
        try:
            response = self._receiver_fn(request)
        except Exception:  # pylint: disable=broad-except
            response.status.code = common_pb.STATUS_UNKNOWN_ERROR
            response.status.error_message = sys.exc_info()
        return response
