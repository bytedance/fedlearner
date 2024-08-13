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

import unittest

import grpc
import grpc_testing

from google.protobuf.descriptor import ServiceDescriptor
from fedlearner_webconsole.proto.rpc.v2 import review_service_pb2
from fedlearner_webconsole.proto import review_pb2

from fedlearner_webconsole.rpc.v2.review_service_client import ReviewServiceClient
from testing.rpc.client import RpcClientTestCase

_SERVICE_DESCRIPTOR: ServiceDescriptor = review_service_pb2.DESCRIPTOR.services_by_name['ReviewService']


class ReviewServiceClientTest(RpcClientTestCase):

    def setUp(self):
        super().setUp()
        self._fake_channel: grpc_testing.Channel = grpc_testing.channel([_SERVICE_DESCRIPTOR],
                                                                        grpc_testing.strict_real_time())
        self._client = ReviewServiceClient(self._fake_channel)

    def test_check_health(self):
        call = self.client_execution_pool.submit(self._client.create_ticket,
                                                 ttype=review_pb2.TicketType.CREATE_PROJECT,
                                                 creator_username='fffff',
                                                 details=review_pb2.TicketDetails(uuid='u1234'))

        _, _, rpc = self._fake_channel.take_unary_unary(_SERVICE_DESCRIPTOR.methods_by_name['CreateTicket'])

        expected_response = review_pb2.Ticket(
            type=review_pb2.TicketType.CREATE_PROJECT,
            creator_username='fffff',
            details=review_pb2.TicketDetails(uuid='u1234'),
            uuid='u4321',
        )
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(call.result(), expected_response)

    def test_get_ticket(self):
        call = self.client_execution_pool.submit(self._client.get_ticket, uuid='u4321')

        _, _, rpc = self._fake_channel.take_unary_unary(_SERVICE_DESCRIPTOR.methods_by_name['GetTicket'])

        expected_response = review_pb2.Ticket(
            type=review_pb2.TicketType.CREATE_PROJECT,
            creator_username='fffff',
            details=review_pb2.TicketDetails(uuid='u1234'),
            uuid='u4321',
        )
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(call.result(), expected_response)


if __name__ == '__main__':
    unittest.main()
