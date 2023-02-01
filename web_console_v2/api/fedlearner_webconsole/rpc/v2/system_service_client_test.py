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
from google.protobuf.struct_pb2 import Struct, Value
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.rpc.v2 import system_service_pb2

from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from testing.rpc.client import RpcClientTestCase

_SERVICE_DESCRIPTOR: ServiceDescriptor = system_service_pb2.DESCRIPTOR.services_by_name['SystemService']


class SystemServiceClientTest(RpcClientTestCase):

    def setUp(self):
        super().setUp()
        self._fake_channel: grpc_testing.Channel = grpc_testing.channel([_SERVICE_DESCRIPTOR],
                                                                        grpc_testing.strict_real_time())
        self._client = SystemServiceClient(self._fake_channel)

    def test_check_health(self):
        call = self.client_execution_pool.submit(self._client.check_health)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CheckHealth'])

        expected_response = system_service_pb2.CheckHealthResponse(
            application_version=common_pb2.ApplicationVersion(
                revision='test rev',
                branch_name='test branch',
                version='1.0.0.1',
                pub_date='20221212',
            ),
            healthy=True,
        )
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(call.result(), expected_response)

    def test_check_health_rpc_error(self):
        call = self.client_execution_pool.submit(self._client.check_health)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CheckHealth'])
        rpc.terminate(
            response=None,
            code=grpc.StatusCode.UNKNOWN,
            trailing_metadata=(),
            details='unknown server error',
        )
        self.assertEqual(call.result(),
                         system_service_pb2.CheckHealthResponse(
                             healthy=False,
                             message='unknown server error',
                         ))

    def test_list_flags(self):
        call = self.client_execution_pool.submit(self._client.list_flags)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['ListFlags'])

        expected_response = system_service_pb2.ListFlagsResponse(flags=Struct(
            fields={
                'flag1': Value(bool_value=True),
                'flag2': Value(string_value='string_value'),
            }))
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(call.result(), {
            'flag1': True,
            'flag2': 'string_value',
        })

    def test_check_tee_enabled(self):
        call = self.client_execution_pool.submit(self._client.check_tee_enabled)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVICE_DESCRIPTOR.methods_by_name['CheckTeeEnabled'])

        expected_response = system_service_pb2.CheckTeeEnabledResponse(tee_enabled=True)
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(call.result(), expected_response)


if __name__ == '__main__':
    unittest.main()
