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

from typing import Optional
import unittest

import grpc
import grpc_testing

from fedlearner_webconsole.proto.testing import service_pb2, service_pb2_grpc
from fedlearner_webconsole.rpc.auth import PROJECT_NAME_HEADER, X_HOST_HEADER
from fedlearner_webconsole.rpc.v2.auth_client_interceptor import AuthClientInterceptor
from google.protobuf.descriptor import ServiceDescriptor
from testing.rpc.client import RpcClientTestCase

_TEST_SERVICE_DESCRIPTOR: ServiceDescriptor = service_pb2.DESCRIPTOR.services_by_name['TestService']


class AuthClientInterceptorTest(RpcClientTestCase):
    _X_HOST = 'fedlearner-webconsole-v2.fl-test.com'

    def set_up(self, project_name: Optional[str] = None) -> service_pb2_grpc.TestServiceStub:
        self._fake_channel: grpc_testing.Channel = grpc_testing.channel([_TEST_SERVICE_DESCRIPTOR],
                                                                        grpc_testing.strict_real_time())
        channel = grpc.intercept_channel(self._fake_channel,
                                         AuthClientInterceptor(x_host=self._X_HOST, project_name=project_name))
        self._stub = service_pb2_grpc.TestServiceStub(channel)

    def test_x_host(self):
        self.set_up()
        call = self.client_execution_pool.submit(self._stub.FakeUnaryUnary, service_pb2.FakeUnaryUnaryRequest())

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _TEST_SERVICE_DESCRIPTOR.methods_by_name['FakeUnaryUnary'])

        self.assertIn((X_HOST_HEADER, self._X_HOST), invocation_metadata)
        rpc.terminate(response=service_pb2.FakeUnaryUnaryResponse(),
                      code=grpc.StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        # Waits for finish
        call.result()

    def test_x_host_unauthenticated(self):
        self.set_up()

        call = self.client_execution_pool.submit(self._stub.FakeUnaryUnary, service_pb2.FakeUnaryUnaryRequest())

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _TEST_SERVICE_DESCRIPTOR.methods_by_name['FakeUnaryUnary'])

        self.assertIn((X_HOST_HEADER, self._X_HOST), invocation_metadata)
        rpc.terminate(response=service_pb2.FakeUnaryUnaryResponse(),
                      code=grpc.StatusCode.UNAUTHENTICATED,
                      trailing_metadata=(),
                      details=None)
        with self.assertRaises(grpc.RpcError) as cm:
            call.result()
        self.assertEqual(cm.exception.code(), grpc.StatusCode.UNAUTHENTICATED)

    def test_project_name(self):
        self.set_up(project_name='test-project-113')

        call = self.client_execution_pool.submit(self._stub.FakeUnaryUnary, service_pb2.FakeUnaryUnaryRequest())

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _TEST_SERVICE_DESCRIPTOR.methods_by_name['FakeUnaryUnary'])

        self.assertIn((X_HOST_HEADER, self._X_HOST), invocation_metadata)
        self.assertIn((PROJECT_NAME_HEADER, 'test-project-113'), invocation_metadata)
        rpc.terminate(response=service_pb2.FakeUnaryUnaryResponse(),
                      code=grpc.StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        # Waits for finish
        call.result()

    def test_project_name_unicode(self):
        self.set_up(project_name='test中文')

        call = self.client_execution_pool.submit(self._stub.FakeUnaryUnary, service_pb2.FakeUnaryUnaryRequest())

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _TEST_SERVICE_DESCRIPTOR.methods_by_name['FakeUnaryUnary'])

        self.assertIn((X_HOST_HEADER, self._X_HOST), invocation_metadata)
        self.assertIn((PROJECT_NAME_HEADER, 'dGVzdOS4reaWhw=='), invocation_metadata)
        rpc.terminate(response=service_pb2.FakeUnaryUnaryResponse(),
                      code=grpc.StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        # Waits for finish
        call.result()


if __name__ == '__main__':
    unittest.main()
