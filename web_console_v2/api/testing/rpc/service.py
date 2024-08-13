# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import grpc

from fedlearner_webconsole.proto.testing import service_pb2_grpc
from fedlearner_webconsole.proto.testing.service_pb2 import FakeUnaryUnaryResponse, FakeStreamStreamResponse, \
    FakeUnaryUnaryRequest


class TestService(service_pb2_grpc.TestServiceServicer):

    def FakeUnaryUnary(self, request: FakeUnaryUnaryRequest, context: grpc.ServicerContext):
        return FakeUnaryUnaryResponse()

    def FakeStreamStream(self, request_iterator, context):
        for _ in request_iterator:
            yield FakeStreamStreamResponse()
