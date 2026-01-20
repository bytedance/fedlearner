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

import time
from typing import Optional
import unittest
import grpc
from datetime import datetime, timedelta
from concurrent import futures

from unittest.mock import patch

from google.protobuf.struct_pb2 import Value
from google.protobuf.wrappers_pb2 import BoolValue

from testing.no_web_server_test_case import NoWebServerTestCase
from testing.dataset import FakeDatasetJobConfiger
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.rpc.v2 import system_service_pb2_grpc
from fedlearner_webconsole.proto.rpc.v2.system_service_pb2 import CheckHealthRequest
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto import dataset_pb2, project_pb2, service_pb2, service_pb2_grpc
from fedlearner_webconsole.proto.metrics_pb2 import ModelJobMetrics
from fedlearner_webconsole.auth.models import Session
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.rpc.v2.auth_server_interceptor import AuthServerInterceptor
from fedlearner_webconsole.rpc.server import RPCServerServicer, RpcServer, rpc_server
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobState, DatasetKindV2, \
    DatasetType, ProcessedDataset
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobGroup, ModelJobType
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.utils.proto import to_json
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.review.common import NO_CENTRAL_SERVER_UUID

_FAKE_SYSTEM_INFO = SystemInfo(
    name='test',
    domain_name='fl-participant.com',
    pure_domain_name='participant',
)


def make_check_auth_info(self, auth_info: Optional[service_pb2.ProjAuthInfo], context: Optional[grpc.ServicerContext],
                         session: Session):
    project = Project(id=1, name='test')
    participant = Participant(id=1, name='participant', domain_name='test_domain')
    return project, participant


class ServerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        listen_port = 1991
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=20), interceptors=[AuthServerInterceptor()])
        service_pb2_grpc.add_WebConsoleV2ServiceServicer_to_server(RPCServerServicer(RpcServer()), self._server)
        self._server.add_insecure_port(f'[::]:{listen_port}')
        self._server.start()

        self._stub = service_pb2_grpc.WebConsoleV2ServiceStub(grpc.insecure_channel(target=f'localhost:{listen_port}'))

    def tearDown(self):
        self._server.stop(5)
        return super().tearDown()

    @patch('fedlearner_webconsole.rpc.server.RpcServer.check_auth_info', lambda *args: ('test_project', 'party_1'))
    def test_get_dataset_job_unexist(self):
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.GetDatasetJob(service_pb2.GetDatasetJobRequest(auth_info=None, uuid='u1234'))

        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    @patch('fedlearner_webconsole.dataset.services.DatasetJobConfiger.from_kind',
           lambda *args: FakeDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.rpc.server.RpcServer.check_auth_info', lambda *args: ('test_project', 'party_1'))
    def test_get_dataset_job(self):
        request = service_pb2.GetDatasetJobRequest(auth_info=None, uuid='dataset_job_uuid')
        # no dataset_job
        with self.assertRaises(grpc.RpcError):
            self._stub.GetDatasetJob(request)
        # check no output_dataset and workflow failed
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job_uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=0,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.RUNNING,
                                     coordinator_id=0,
                                     workflow_id=0)
            session.add(dataset_job)
            session.commit()
        resp = self._stub.GetDatasetJob(request)
        self.assertEqual(resp.dataset_job.uuid, dataset_job.uuid)
        self.assertEqual(resp.dataset_job.result_dataset_uuid, '')
        self.assertEqual(resp.dataset_job.is_ready, False)
        # check is_ready successed
        with db.session_scope() as session:
            dataset = Dataset(id=2,
                              name='output dataset',
                              uuid='result_dataset_uuid',
                              path='/data/dataset/321',
                              project_id=1,
                              created_at=datetime(2012, 1, 14, 12, 0, 7),
                              dataset_kind=DatasetKindV2.PROCESSED)
            session.add(dataset)
            workflow = Workflow(id=1, project_id=1, name='test workflow', uuid='dataset_job_uuid')
            session.add(workflow)
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.workflow_id = 1
            dataset_job.output_dataset_id = 2
            session.commit()
        resp = self._stub.GetDatasetJob(request)
        self.assertEqual(resp.dataset_job.uuid, dataset_job.uuid)
        self.assertEqual(resp.dataset_job.result_dataset_uuid, 'result_dataset_uuid')
        self.assertEqual(resp.dataset_job.is_ready, True)

    @patch('fedlearner_webconsole.rpc.server.RpcServer.check_auth_info', make_check_auth_info)
    @patch('fedlearner_webconsole.rpc.server.SettingService.get_system_info', lambda: _FAKE_SYSTEM_INFO)
    def test_create_dataset_job(self):
        with db.session_scope() as session:
            project = Project(id=1, name='test')
            session.add(project)
            dataset = Dataset(id=1,
                              name='input dataset',
                              uuid='raw_dataset_uuid',
                              path='/data/dataset/321',
                              is_published=True,
                              project_id=1,
                              created_at=datetime(2012, 1, 14, 12, 0, 7),
                              dataset_kind=DatasetKindV2.RAW)
            session.add(dataset)
            session.commit()
        dataset_job = DatasetJob(id=1,
                                 uuid='dataset_job_uuid',
                                 project_id=1,
                                 input_dataset_id=1,
                                 output_dataset_id=2,
                                 kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                 state=DatasetJobState.RUNNING,
                                 coordinator_id=0,
                                 workflow_id=1)
        dataset_job_parameter = dataset_pb2.DatasetJob(
            uuid=dataset_job.uuid,
            kind=dataset_job.kind.value,
            global_configs=dataset_pb2.DatasetJobGlobalConfigs(global_configs={
                _FAKE_SYSTEM_INFO.pure_domain_name: dataset_pb2.DatasetJobConfig(dataset_uuid='raw_dataset_uuid')
            }),
            workflow_definition=WorkflowDefinition(group_alias='test'),
            result_dataset_uuid='dataset_uuid',
            result_dataset_name='dataset_name',
            creator_username='test user')
        request = service_pb2.CreateDatasetJobRequest(auth_info=None,
                                                      dataset_job=dataset_job_parameter,
                                                      ticket_uuid=NO_CENTRAL_SERVER_UUID)
        self._stub.CreateDatasetJob(request)
        with db.session_scope() as session:
            dataset = session.query(ProcessedDataset).filter_by(uuid='dataset_uuid').first()
            self.assertEqual(dataset.name, 'dataset_name')
            self.assertEqual(dataset.dataset_kind, DatasetKindV2.PROCESSED)
            self.assertEqual(len(dataset.data_batches), 1)
            self.assertEqual(dataset.is_published, True)
            dataset_job = session.query(DatasetJob).filter_by(uuid='dataset_job_uuid').first()
            self.assertIsNotNone(dataset_job)
            self.assertEqual(dataset_job.output_dataset_id, dataset.id)
            self.assertEqual(dataset_job.creator_username, 'test user')
            self.assertIsNone(dataset_job.time_range)

        # test with time_range
        dataset_job = DatasetJob(id=2,
                                 uuid='dataset_job_uuid with time_range',
                                 project_id=1,
                                 input_dataset_id=1,
                                 output_dataset_id=2,
                                 kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                 state=DatasetJobState.RUNNING,
                                 coordinator_id=0,
                                 workflow_id=1,
                                 time_range=timedelta(days=1))
        dataset_job_parameter = dataset_pb2.DatasetJob(
            uuid=dataset_job.uuid,
            kind=dataset_job.kind.value,
            global_configs=dataset_pb2.DatasetJobGlobalConfigs(global_configs={
                _FAKE_SYSTEM_INFO.pure_domain_name: dataset_pb2.DatasetJobConfig(dataset_uuid='raw_dataset_uuid')
            }),
            workflow_definition=WorkflowDefinition(group_alias='test'),
            result_dataset_uuid='dataset_uuid wit time_range',
            result_dataset_name='dataset_name',
            creator_username='test user',
            time_range=dataset_job.time_range_pb)
        request = service_pb2.CreateDatasetJobRequest(auth_info=None,
                                                      dataset_job=dataset_job_parameter,
                                                      ticket_uuid=NO_CENTRAL_SERVER_UUID)
        self._stub.CreateDatasetJob(request)
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).filter_by(uuid='dataset_job_uuid with time_range').first()
            self.assertEqual(dataset_job.time_range, timedelta(days=1))

    @patch('fedlearner_webconsole.rpc.server.RpcServer.check_auth_info', make_check_auth_info)
    @patch('fedlearner_webconsole.rpc.server.SettingService.get_system_info', lambda: _FAKE_SYSTEM_INFO)
    def test_create_dataset_job_has_stage(self):
        with db.session_scope() as session:
            project = Project(id=1, name='test')
            session.add(project)
            streaming_dataset = Dataset(id=1,
                                        name='input streaming_dataset',
                                        uuid='raw_dataset_uuid',
                                        path='/data/dataset/321',
                                        is_published=True,
                                        project_id=1,
                                        created_at=datetime(2012, 1, 14, 12, 0, 7),
                                        dataset_kind=DatasetKindV2.RAW,
                                        dataset_type=DatasetType.STREAMING.value)
            session.add(streaming_dataset)
            session.commit()
        dataset_job_parameter = dataset_pb2.DatasetJob(
            uuid='dataset_job_uuid',
            kind=DatasetJobKind.DATA_ALIGNMENT.value,
            global_configs=dataset_pb2.DatasetJobGlobalConfigs(global_configs={
                _FAKE_SYSTEM_INFO.pure_domain_name: dataset_pb2.DatasetJobConfig(dataset_uuid='raw_dataset_uuid')
            }),
            workflow_definition=WorkflowDefinition(group_alias='test'),
            result_dataset_uuid='dataset_uuid',
            result_dataset_name='dataset_name',
            has_stages=True,
        )
        participants_info = project_pb2.ParticipantsInfo(
            participants_map={
                'test_participant_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                'test_participant_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                'participant': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name)
            })
        dataset_parameter = dataset_pb2.Dataset(participants_info=participants_info, creator_username='test user')
        request = service_pb2.CreateDatasetJobRequest(auth_info=None,
                                                      dataset_job=dataset_job_parameter,
                                                      ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                                      dataset=dataset_parameter)
        self._stub.CreateDatasetJob(request)
        with db.session_scope() as session:
            dataset = session.query(ProcessedDataset).filter_by(uuid='dataset_uuid').first()
            self.assertEqual(dataset.name, 'dataset_name')
            self.assertEqual(dataset.dataset_kind, DatasetKindV2.PROCESSED)
            self.assertEqual(len(dataset.data_batches), 0)
            self.assertEqual(dataset.is_published, True)
            self.assertEqual(dataset.dataset_type, DatasetType.STREAMING)
            self.assertEqual(dataset.creator_username, 'test user')
            dataset_job = session.query(DatasetJob).filter_by(uuid='dataset_job_uuid').first()
            self.assertIsNotNone(dataset_job)
            self.assertEqual(dataset_job.output_dataset_id, dataset.id)
            self.assertEqual(dataset.ticket_uuid, NO_CENTRAL_SERVER_UUID)
            self.assertEqual(dataset.ticket_status, TicketStatus.APPROVED)
            expected_participants_info = project_pb2.ParticipantsInfo(
                participants_map={
                    'test_participant_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'test_participant_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'participant': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            self.assertEqual(dataset.get_participants_info(), expected_participants_info)

    @patch('fedlearner_webconsole.rpc.server.RpcServer.check_auth_info', make_check_auth_info)
    def test_update_workflow(self):
        uuid = 'u1ff0ab5596bb487e96c'
        with db.session_scope() as session:
            var1 = Variable(name='hello',
                            value_type=Variable.NUMBER,
                            typed_value=Value(number_value=1),
                            access_mode=Variable.PEER_WRITABLE)
            var2 = Variable(name='hello',
                            value_type=Variable.NUMBER,
                            typed_value=Value(number_value=1),
                            access_mode=Variable.PEER_READABLE)
            jd = JobDefinition(name='test1', yaml_template='{}', variables=[var1, var2])
            wd = WorkflowDefinition(job_definitions=[jd])
            workflow = Workflow(
                name='test-workflow',
                uuid=uuid,
                project_id=1,
                config=wd.SerializeToString(),
            )
            session.add(workflow)
            session.flush()
            job = Job(name='test_job',
                      config=jd.SerializeToString(),
                      workflow_id=workflow.id,
                      job_type=JobType(1),
                      project_id=1,
                      is_disabled=False)
            session.add(job)
            session.flush()
            workflow.job_ids = str(job.id)
            session.commit()
        var1 = Variable(name='hello',
                        value_type=Variable.NUMBER,
                        typed_value=Value(number_value=2),
                        access_mode=Variable.PEER_WRITABLE)
        var2 = Variable(name='hello',
                        value_type=Variable.NUMBER,
                        typed_value=Value(number_value=2),
                        access_mode=Variable.PEER_READABLE)
        jd = JobDefinition(name='test1', yaml_template='{}', variables=[var1, var2])
        wd = WorkflowDefinition(job_definitions=[jd])
        request = service_pb2.UpdateWorkflowRequest(auth_info=None, workflow_uuid=uuid, config=wd)
        self._stub.UpdateWorkflow(request)
        with db.session_scope() as session:
            workflow = session.query(Workflow).filter_by(uuid=uuid).first()
            self.assertEqual(workflow.get_config().job_definitions[0].variables[0].typed_value, Value(number_value=2))
            self.assertEqual(workflow.get_config().job_definitions[0].variables[1].typed_value, Value(number_value=1))
            jd = workflow.get_jobs(session)[0].get_config()
            self.assertEqual(jd.variables[0].typed_value, Value(number_value=2))
            self.assertEqual(jd.variables[1].typed_value, Value(number_value=1))

    @patch('fedlearner_webconsole.rpc.server.RpcServer.check_auth_info', make_check_auth_info)
    @patch('fedlearner_webconsole.mmgr.service.ModelJobService.query_metrics')
    def test_get_model_job(self, mock_query_metrics):
        metrics = ModelJobMetrics()
        metric = metrics.train.get_or_create('acc')
        metric.steps.extend([1, 2, 3])
        metric.values.extend([1.0, 2.0, 3.0])
        mock_query_metrics.return_value = metrics
        with db.session_scope() as session:
            job = Job(name='uuid-job',
                      project_id=1,
                      workflow_id=1,
                      job_type=JobType.NN_MODEL_TRANINING,
                      state=JobState.COMPLETED)
            workflow = Workflow(id=1, name='workflow', uuid='uuid')
            group = ModelJobGroup(id=1, name='group', uuid='uuid', project_id=1)
            model_job = ModelJob(id=1,
                                 name='job',
                                 uuid='uuid',
                                 group_id=1,
                                 project_id=1,
                                 metric_is_public=False,
                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                 model_job_type=ModelJobType.TRAINING,
                                 workflow_uuid='uuid',
                                 job_name='uuid-job')
            session.add_all([job, workflow, group, model_job])
            session.commit()
        request = service_pb2.GetModelJobRequest(auth_info=None, uuid='uuid', need_metrics=True)
        resp = self._stub.GetModelJob(request)
        mock_query_metrics.assert_not_called()
        expected_resp = service_pb2.GetModelJobResponse(name='job',
                                                        uuid='uuid',
                                                        algorithm_type='NN_VERTICAL',
                                                        model_job_type='TRAINING',
                                                        group_uuid='uuid',
                                                        state='INVALID',
                                                        metric_is_public=BoolValue(value=False))
        self.assertEqual(resp, expected_resp)
        with db.session_scope() as session:
            model_job: ModelJob = session.query(ModelJob).get(1)
            model_job.metric_is_public = True
            session.commit()
        resp = self._stub.GetModelJob(request)
        mock_query_metrics.assert_called()
        expected_resp.metric_is_public.MergeFrom(BoolValue(value=True))
        expected_resp.metrics = to_json(metrics)
        self.assertEqual(resp, expected_resp)


class RpcServerTest(NoWebServerTestCase):

    def test_smoke_test(self):
        rpc_server.start(13546)
        # Waits for server ready
        time.sleep(2)
        stub = system_service_pb2_grpc.SystemServiceStub(grpc.insecure_channel(target='localhost:13546'))
        self.assertIsNotNone(
            stub.CheckHealth(CheckHealthRequest(),
                             metadata=[('ssl-client-subject-dn',
                                        'CN=aaa.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN')]))
        rpc_server.stop()


if __name__ == '__main__':
    unittest.main()
