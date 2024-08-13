# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from datetime import datetime
from google.protobuf.wrappers_pb2 import BoolValue
from google.protobuf import empty_pb2

from fedlearner_webconsole.middleware.request_id import GrpcRequestIdMiddleware
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction, TransactionData, CreateModelJobData
from fedlearner_webconsole.participant.models import Participant

from fedlearner_webconsole.proto.service_pb2 import DESCRIPTOR, CheckPeerConnectionRequest, \
    CheckPeerConnectionResponse, CreateDatasetJobRequest, TwoPcRequest, TwoPcResponse
from fedlearner_webconsole.rpc.client import RpcClient, _build_grpc_stub
from fedlearner_webconsole.project.models import Project as ProjectModel
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.common_pb2 import (Status, StatusCode as FedLearnerStatusCode)
from fedlearner_webconsole.proto.dataset_pb2 import ParticipantDatasetRef
from fedlearner_webconsole.proto.service_pb2 import (CheckConnectionRequest, ProjAuthInfo)
from fedlearner_webconsole.proto.service_pb2 import CheckConnectionResponse, \
    CheckJobReadyResponse, CheckJobReadyRequest, ListParticipantDatasetsRequest, ListParticipantDatasetsResponse, \
    GetModelJobRequest, GetModelJobResponse
from fedlearner_webconsole.proto import dataset_pb2, project_pb2
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.dataset.models import DatasetFormat, DatasetKindV2
from testing.rpc.client import RpcClientTestCase
from testing.fake_time_patcher import FakeTimePatcher

TARGET_SERVICE = DESCRIPTOR.services_by_name['WebConsoleV2Service']


class RpcClientTest(RpcClientTestCase):
    _TEST_PROJECT_NAME = 'test-project'
    _TEST_RECEIVER_NAME = 'test-receiver'
    _TEST_URL = 'localhost:123'
    _X_HOST_HEADER_KEY = 'x-host'
    _TEST_X_HOST = 'fedlearner-webconsole-v2.fl-test.com'
    _TEST_SELF_DOMAIN_NAME = 'fl-test-self.com'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        participant = Participant(name=cls._TEST_RECEIVER_NAME, domain_name='fl-test.com')
        job = Job(name='test-job')

        cls._participant = participant
        cls._project = ProjectModel(name=cls._TEST_PROJECT_NAME)
        cls._job = job

        # Builds a testing channel
        cls._fake_channel = grpc_testing.channel(DESCRIPTOR.services_by_name.values(), grpc_testing.strict_real_time())
        cls._fake_channel_patcher = patch('fedlearner_webconsole.rpc.client.grpc.insecure_channel')
        cls._mock_build_channel = cls._fake_channel_patcher.start()
        cls._mock_build_channel.return_value = cls._fake_channel

    @classmethod
    def tearDownClass(cls):
        cls._fake_channel_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._client = RpcClient.from_project_and_participant(self._project.name, self._project.token,
                                                              self._participant.domain_name)

    def test_build_grpc_stub(self):
        fake_timer = FakeTimePatcher()
        fake_timer.start()
        authority = 'fl-test-client-auth.com'

        # Don't know where to put this check - -
        self._mock_build_channel.assert_called_once_with(
            options=[('grpc.default_authority', 'fl-test-client-auth.com')],
            target='fedlearner-stack-ingress-nginx-controller.default.svc:80')
        self._mock_build_channel.reset_mock()

        _build_grpc_stub(self._TEST_URL, authority)
        self._mock_build_channel.assert_called_once_with(options=[('grpc.default_authority', authority)],
                                                         target=self._TEST_URL)
        _build_grpc_stub(self._TEST_URL, authority)
        self.assertEqual(self._mock_build_channel.call_count, 1)
        # Ticks 61 seconds to timeout
        fake_timer.interrupt(61)
        _build_grpc_stub(self._TEST_URL, authority)
        self.assertEqual(self._mock_build_channel.call_count, 2)
        fake_timer.stop()

    @patch('fedlearner_webconsole.middleware.request_id.get_current_request_id')
    def test_request_id_in_metadata(self, mock_get_current_request_id):
        mock_get_current_request_id.return_value = 'test-request-id'

        call = self.client_execution_pool.submit(self._client.check_connection)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckConnection'])
        self.assertIn((GrpcRequestIdMiddleware.REQUEST_HEADER_NAME, 'test-request-id'), invocation_metadata)
        # We don't care the result
        rpc.terminate(response=CheckConnectionResponse(), code=StatusCode.OK, trailing_metadata=(), details=None)

    def test_check_connection(self):
        call = self.client_execution_pool.submit(self._client.check_connection)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckConnection'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)
        self.assertEqual(
            request,
            CheckConnectionRequest(auth_info=ProjAuthInfo(project_name=self._project.name,
                                                          target_domain=self._participant.domain_name,
                                                          auth_token=self._project.token)))

        expected_status = Status(code=FedLearnerStatusCode.STATUS_SUCCESS, msg='test')
        rpc.terminate(response=CheckConnectionResponse(status=expected_status),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result().status, expected_status)

    def test_check_peer_connection(self):
        call = self.client_execution_pool.submit(self._client.check_peer_connection)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckPeerConnection'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)

        self.assertEqual(request, CheckPeerConnectionRequest())

        expected_status = Status(code=FedLearnerStatusCode.STATUS_SUCCESS, msg='received check request successfully!')
        rpc.terminate(response=CheckPeerConnectionResponse(status=expected_status,
                                                           application_version={'version': '2.0.1.5'}),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result().status, expected_status)
        self.assertEqual(call.result().application_version.version, '2.0.1.5')

    def test_check_job_ready(self):
        call = self.client_execution_pool.submit(self._client.check_job_ready, self._job.name)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CheckJobReady'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)
        self.assertEqual(
            request,
            CheckJobReadyRequest(job_name=self._job.name,
                                 auth_info=ProjAuthInfo(project_name=self._project.name,
                                                        target_domain=self._participant.domain_name,
                                                        auth_token=self._project.token)))

        expected_status = Status(code=FedLearnerStatusCode.STATUS_SUCCESS, msg='test')
        rpc.terminate(response=CheckJobReadyResponse(status=expected_status),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result().status, expected_status)

    def test_run_two_pc(self):
        transaction_data = TransactionData(create_model_job_data=CreateModelJobData(model_job_name='test model name'))
        call = self.client_execution_pool.submit(self._client.run_two_pc,
                                                 transaction_uuid='test-id',
                                                 two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                                 action=TwoPcAction.PREPARE,
                                                 data=transaction_data)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['Run2Pc'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)
        self.assertEqual(
            request,
            TwoPcRequest(auth_info=ProjAuthInfo(project_name=self._project.name,
                                                target_domain=self._participant.domain_name,
                                                auth_token=self._project.token),
                         transaction_uuid='test-id',
                         type=TwoPcType.CREATE_MODEL_JOB,
                         action=TwoPcAction.PREPARE,
                         data=transaction_data))

        expected_status = Status(code=FedLearnerStatusCode.STATUS_SUCCESS, msg='test run two pc')
        rpc.terminate(response=TwoPcResponse(status=expected_status),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result().status, expected_status)

    def test_list_participant_datasets(self):
        call = self.client_execution_pool.submit(self._client.list_participant_datasets)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['ListParticipantDatasets'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)
        self.assertEqual(
            request,
            ListParticipantDatasetsRequest(auth_info=ProjAuthInfo(project_name=self._project.name,
                                                                  target_domain=self._participant.domain_name,
                                                                  auth_token=self._project.token)))

        dataref = ParticipantDatasetRef(uuid='1',
                                        name='dataset',
                                        format=DatasetFormat.TABULAR.name,
                                        file_size=0,
                                        updated_at=to_timestamp(datetime(2012, 1, 14, 12, 0, 5)),
                                        dataset_kind=DatasetKindV2.RAW.name)
        rpc.terminate(response=ListParticipantDatasetsResponse(participant_datasets=[dataref]),
                      code=StatusCode.OK,
                      trailing_metadata=(),
                      details=None)
        self.assertEqual(call.result(), ListParticipantDatasetsResponse(participant_datasets=[dataref]))

    def test_get_model_job(self):
        call = self.client_execution_pool.submit(self._client.get_model_job, model_job_uuid='uuid', need_metrics=True)

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['GetModelJob'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)
        self.assertEqual(
            request,
            GetModelJobRequest(auth_info=ProjAuthInfo(project_name=self._project.name,
                                                      target_domain=self._participant.domain_name,
                                                      auth_token=self._project.token),
                               uuid='uuid',
                               need_metrics=True))

        expected_metric = BoolValue(value=True)
        resp = GetModelJobResponse(metric_is_public=expected_metric)
        rpc.terminate(response=resp, code=StatusCode.OK, trailing_metadata=(), details=None)
        self.assertEqual(call.result(), GetModelJobResponse(metric_is_public=expected_metric))

    def test_create_dataset_job(self):
        participants_info = project_pb2.ParticipantsInfo(
            participants_map={
                'test_participant_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                'test_participant_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name)
            })
        call = self.client_execution_pool.submit(self._client.create_dataset_job,
                                                 dataset_job=dataset_pb2.DatasetJob(uuid='test'),
                                                 ticket_uuid='test ticket_uuid',
                                                 dataset=dataset_pb2.Dataset(participants_info=participants_info))

        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            TARGET_SERVICE.methods_by_name['CreateDatasetJob'])

        self.assertIn((self._X_HOST_HEADER_KEY, self._TEST_X_HOST), invocation_metadata)
        self.assertEqual(
            request,
            CreateDatasetJobRequest(auth_info=ProjAuthInfo(project_name=self._project.name,
                                                           target_domain=self._participant.domain_name,
                                                           auth_token=self._project.token),
                                    dataset_job=dataset_pb2.DatasetJob(uuid='test'),
                                    ticket_uuid='test ticket_uuid',
                                    dataset=dataset_pb2.Dataset(participants_info=participants_info)))

        resp = empty_pb2.Empty()
        rpc.terminate(response=resp, code=StatusCode.OK, trailing_metadata=(), details=None)
        self.assertEqual(call.result(), empty_pb2.Empty())


if __name__ == '__main__':
    unittest.main()
