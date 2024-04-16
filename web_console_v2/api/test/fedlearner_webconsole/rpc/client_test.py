# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import unittest
from unittest.mock import patch

import grpc_testing
from grpc import StatusCode
from grpc.framework.foundation import logging_pool

from testing.common import NoWebServerTestCase

from fedlearner_webconsole.proto.service_pb2 import DESCRIPTOR
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.project.models import Project as ProjectModel
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.common_pb2 import (GrpcSpec, Status,
                                                    StatusCode as
                                                    FedLearnerStatusCode)
from fedlearner_webconsole.proto.project_pb2 import Project, Participant
from fedlearner_webconsole.proto.service_pb2 import (CheckConnectionRequest,
                                                     ProjAuthInfo)
from fedlearner_webconsole.proto.service_pb2 import CheckConnectionResponse, \
    CheckJobReadyResponse, CheckJobReadyRequest

TARGET_SERVICE = DESCRIPTOR.services_by_name['WebConsoleV2Service']


class RpcClientTest(NoWebServerTestCase):
    _TEST_PROJECT_NAME = 'test-project'
    _TEST_RECEIVER_NAME = 'test-receiver'
    _TEST_URL = 'localhost:123'
    _TEST_AUTHORITY = 'test-authority'
    _X_HOST_HEADER_KEY = 'x-host'
    _TEST_X_HOST = 'default.fedlearner.webconsole'
    _TEST_SELF_DOMAIN_NAME = 'fl-test-self.com'

    @classmethod
    def setUpClass(cls):

        grpc_spec = GrpcSpec(
            authority=cls._TEST_AUTHORITY,
            extra_headers={cls._X_HOST_HEADER_KEY: cls._TEST_X_HOST})
        participant = Participant(name=cls._TEST_RECEIVER_NAME,
                                  domain_name='fl-test.com',
                                  grpc_spec=grpc_spec)
        project_config = Project(name=cls._TEST_PROJECT_NAME,
                                 token='test-auth-token',
                                 participants=[participant],
                                 variables=[{
                                     'name': 'EGRESS_URL',
                                     'value': cls._TEST_URL
                                 }])
        job = Job(name='test-job')

        cls._participant = participant
        cls._project_config = project_config
        cls._project = ProjectModel(name=cls._TEST_PROJECT_NAME)
        cls._project.set_config(project_config)
        cls._job = job

    def setUp(self):
        self._client_execution_thread_pool = logging_pool.pool(1)

        # Builds a testing channel
        self._fake_channel = grpc_testing.channel(
            DESCRIPTOR.services_by_name.values(),
            grpc_testing.strict_real_time())
        self._build_channel_patcher = patch(
            'fedlearner_webconsole.rpc.client._build_channel')
        self._mock_build_channel = self._build_channel_patcher.start()
        self._mock_build_channel.return_value = self._fake_channel
        self._client = RpcClient(self._project_config, self._participant)

        self._mock_build_channel.assert_called_once_with(
            self._TEST_URL, self._TEST_AUTHORITY)

    def tearDown(self):
        self._build_channel_patcher.stop()
        self._client_execution_thread_pool.shutdown(wait=False)

    def test_check_connection(self):
        call = self._client_execution_thread_pool.submit(
            self._client.check_connection)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckConnection'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST),
                      invocation_metadata)
        self.assertEqual(
            request,
            CheckConnectionRequest(auth_info=ProjAuthInfo(
                project_name=self._project_config.name,
                target_domain=self._participant.domain_name,
                auth_token=self._project_config.token)))

        expected_status = Status(code=FedLearnerStatusCode.STATUS_SUCCESS,
                                 msg='test')
        rpc.terminate(response=CheckConnectionResponse(status=expected_status),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result().status, expected_status)

    def test_check_job_ready(self):
        call = self._client_execution_thread_pool.submit(
            self._client.check_job_ready, self._job.name)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckJobReady'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST),
                      invocation_metadata)
        self.assertEqual(
            request,
            CheckJobReadyRequest(
                job_name=self._job.name,
                auth_info=ProjAuthInfo(
                    project_name=self._project_config.name,
                    target_domain=self._participant.domain_name,
                    auth_token=self._project_config.token)))

        expected_status = Status(code=FedLearnerStatusCode.STATUS_SUCCESS,
                                 msg='test')
        rpc.terminate(response=CheckJobReadyResponse(status=expected_status),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result().status, expected_status)


if __name__ == '__main__':
    unittest.main()
