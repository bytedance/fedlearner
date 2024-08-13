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
from concurrent import futures
from unittest.mock import patch, Mock

import grpc

from google.protobuf.struct_pb2 import Struct, Value

from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.rpc.v2 import system_service_pb2_grpc
from fedlearner_webconsole.proto.rpc.v2.system_service_pb2 import CheckHealthRequest, CheckHealthResponse, \
    ListFlagsRequest, ListFlagsResponse, CheckTeeEnabledRequest, CheckTeeEnabledResponse
from fedlearner_webconsole.rpc.v2.system_service_server import SystemGrpcService
from fedlearner_webconsole.utils.app_version import ApplicationVersion
from testing.no_web_server_test_case import NoWebServerTestCase


class SystemServiceTest(NoWebServerTestCase):
    LISTEN_PORT = 1999

    def setUp(self):
        super().setUp()
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        system_service_pb2_grpc.add_SystemServiceServicer_to_server(SystemGrpcService(), self._server)
        self._server.add_insecure_port(f'[::]:{self.LISTEN_PORT}')
        self._server.start()

        self._stub = system_service_pb2_grpc.SystemServiceStub(
            grpc.insecure_channel(target=f'localhost:{self.LISTEN_PORT}'))

    def tearDown(self):
        self._server.stop(5)
        return super().tearDown()

    @patch('fedlearner_webconsole.rpc.v2.system_service_server.SettingService.get_application_version')
    def test_check_health(self, mock_get_application_version: Mock):
        mock_get_application_version.return_value = ApplicationVersion(
            revision='test rev',
            branch_name='test branch',
            version='1.0.0.1',
            pub_date='20220101',
        )

        resp = self._stub.CheckHealth(CheckHealthRequest())
        self.assertEqual(
            resp,
            CheckHealthResponse(
                application_version=common_pb2.ApplicationVersion(
                    revision='test rev',
                    branch_name='test branch',
                    version='1.0.0.1',
                    pub_date='20220101',
                ),
                healthy=True,
            ))

    @patch('fedlearner_webconsole.rpc.v2.system_service_server.get_flags')
    def test_list_flags(self, mock_flags: Mock):
        mock_flags.return_value = {
            'flag1': True,
            'flag2': 'string_value',
            'flag3': {
                'key': 'value',
            },
        }

        resp = self._stub.ListFlags(ListFlagsRequest())
        self.assertEqual(
            resp,
            ListFlagsResponse(flags=Struct(
                fields={
                    'flag1': Value(bool_value=True),
                    'flag2': Value(string_value='string_value'),
                    'flag3': Value(struct_value=Struct(fields={
                        'key': Value(string_value='value'),
                    }))
                })))

    def test_check_tee_enabled(self):
        Flag.TEE_MACHINE_DEPLOYED.value = True
        resp = self._stub.CheckTeeEnabled(CheckTeeEnabledRequest())
        self.assertEqual(resp, CheckTeeEnabledResponse(tee_enabled=True))
        Flag.TEE_MACHINE_DEPLOYED.value = False
        resp = self._stub.CheckTeeEnabled(CheckTeeEnabledRequest())
        self.assertEqual(resp, CheckTeeEnabledResponse(tee_enabled=False))


if __name__ == '__main__':
    unittest.main()
