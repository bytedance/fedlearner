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
from unittest.mock import MagicMock, Mock, call, patch
import grpc
import grpc_testing

from fedlearner_webconsole.proto.testing import service_pb2
from fedlearner_webconsole.rpc.v2.client_base import (ParticipantProjectRpcClient, ParticipantRpcClient,
                                                      build_grpc_channel, get_nginx_controller_url)
from testing.fake_time_patcher import FakeTimePatcher
from testing.rpc.client import RpcClientTestCase


class GetNginxControllerUrlTest(unittest.TestCase):

    def test_prod(self):
        self.assertEqual(
            get_nginx_controller_url(),
            'fedlearner-stack-ingress-nginx-controller.default.svc:80',
        )

    @patch('envs.Envs.DEBUG', 'True')
    @patch('envs.Envs.GRPC_SERVER_URL', 'xxx.default.svc:443')
    def test_custom_url(self):
        self.assertEqual(
            get_nginx_controller_url(),
            'xxx.default.svc:443',
        )


class BuildGrpcChannelTest(RpcClientTestCase):

    def setUp(self):
        super().setUp()
        self._insecure_channel_patcher = patch('fedlearner_webconsole.rpc.v2.client_base.grpc.insecure_channel')
        self._mock_insecure_channel: Mock = self._insecure_channel_patcher.start()
        self._mock_insecure_channel.return_value = grpc_testing.channel(
            service_pb2.DESCRIPTOR.services_by_name.values(), grpc_testing.strict_real_time())

    def tearDown(self):
        self._insecure_channel_patcher.stop()
        super().tearDown()

    @patch('fedlearner_webconsole.rpc.v2.client_base.AuthClientInterceptor', spec=grpc.UnaryUnaryClientInterceptor)
    def test_build_same_channel(self, mock_auth_client_interceptor: Mock):
        fake_timer = FakeTimePatcher()
        fake_timer.start()
        nginx_controller_url = 'test-nginx.default.svc:80'
        channel1 = build_grpc_channel(nginx_controller_url, 'fl-test1.com')
        # Within 60s
        channel2 = build_grpc_channel(nginx_controller_url, 'fl-test1.com')
        # Checks if it is the same instance
        self.assertTrue(channel1 is channel2)
        self._mock_insecure_channel.assert_called_once_with(
            target=nginx_controller_url,
            options=[('grpc.default_authority', 'fl-test1-client-auth.com')],
        )
        mock_auth_client_interceptor.assert_called_once_with(
            x_host='fedlearner-webconsole-v2.fl-test1.com',
            project_name=None,
        )

        # Ticks 62 seconds to timeout
        fake_timer.interrupt(62)
        channel3 = build_grpc_channel(nginx_controller_url, 'fl-test1.com')
        self.assertTrue(channel3 is not channel1)
        self.assertEqual(self._mock_insecure_channel.call_count, 2)
        self.assertEqual(mock_auth_client_interceptor.call_count, 2)

    @patch('fedlearner_webconsole.rpc.v2.client_base.AuthClientInterceptor', spec=grpc.UnaryUnaryClientInterceptor)
    def test_build_different_channels(self, mock_auth_client_interceptor: Mock):
        nginx_controller_url = 'test.default.svc:80'
        channel1 = build_grpc_channel(nginx_controller_url, 'fl-test1.com')
        channel2 = build_grpc_channel(nginx_controller_url, 'fl-test1.com', project_name='test-project')
        self.assertTrue(channel1 is not channel2)

        self.assertEqual(self._mock_insecure_channel.call_args_list, [
            call(
                target=nginx_controller_url,
                options=[('grpc.default_authority', 'fl-test1-client-auth.com')],
            ),
            call(
                target=nginx_controller_url,
                options=[('grpc.default_authority', 'fl-test1-client-auth.com')],
            ),
        ])
        self.assertEqual(mock_auth_client_interceptor.call_args_list, [
            call(
                x_host='fedlearner-webconsole-v2.fl-test1.com',
                project_name=None,
            ),
            call(
                x_host='fedlearner-webconsole-v2.fl-test1.com',
                project_name='test-project',
            ),
        ])


class _FakeRpcClient(ParticipantRpcClient, ParticipantProjectRpcClient):

    def __init__(self, channel):
        super().__init__(channel)
        self.channel = channel


class ParticipantRpcClientTest(unittest.TestCase):

    @patch('fedlearner_webconsole.rpc.v2.client_base.build_grpc_channel')
    def test_from_participant(self, mock_build_grpc_channel: Mock):
        fake_channel = MagicMock()
        mock_build_grpc_channel.return_value = fake_channel

        domain_name = 'fl-test.com'
        fake_client = _FakeRpcClient.from_participant(domain_name=domain_name)
        self.assertTrue(fake_client.channel is fake_channel)
        mock_build_grpc_channel.assert_called_once_with(
            'fedlearner-stack-ingress-nginx-controller.default.svc:80',
            domain_name,
        )


class ParticipantProjectRpcClientTest(unittest.TestCase):

    @patch('fedlearner_webconsole.rpc.v2.client_base.build_grpc_channel')
    def test_from_project_and_participant(self, mock_build_grpc_channel: Mock):
        fake_channel = MagicMock()
        mock_build_grpc_channel.return_value = fake_channel

        domain_name = 'fl-test.com'
        project_name = 'test-prrrr'
        fake_client = _FakeRpcClient.from_project_and_participant(domain_name, project_name)
        self.assertTrue(fake_client.channel is fake_channel)
        mock_build_grpc_channel.assert_called_once_with(
            'fedlearner-stack-ingress-nginx-controller.default.svc:80',
            domain_name,
            project_name,
        )


if __name__ == '__main__':
    unittest.main()
