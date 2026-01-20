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

from datetime import datetime, timedelta
import unittest
from unittest.mock import patch, MagicMock
import grpc
from google.protobuf.empty_pb2 import Empty
from concurrent import futures
from testing.dataset import FakeDatasetJobConfiger
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.rpc.client import FakeRpcError
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.rpc.auth import SSL_CLIENT_SUBJECT_DN_HEADER, PROJECT_NAME_HEADER
from fedlearner_webconsole.proto.rpc.v2 import job_service_pb2_grpc
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.rpc.v2.job_service_server import JobServiceServicer
from fedlearner_webconsole.rpc.v2.utils import get_grpc_context_info
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, DatasetJob, DatasetJobKind, DatasetJobStage, \
    DatasetJobState, DatasetKindV2, DatasetType, DatasetJobSchedulerState
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobStatus, TrustedJobType
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, AlgorithmType
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobGroup, ModelJobType, ModelJobRole, ModelJobStatus, \
    AuthStatus as ModelAuthStatus, GroupAutoUpdateStatus
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, ModelJobConfig, AlgorithmProjectList, \
    ModelJobPb, ModelJobGroupPb
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import CreateModelJobRequest, InformTrustedJobGroupRequest, \
    UpdateTrustedJobGroupRequest, DeleteTrustedJobGroupRequest, GetTrustedJobGroupRequest, \
    GetTrustedJobGroupResponse, CreateDatasetJobStageRequest, GetDatasetJobStageRequest, CreateModelJobGroupRequest, \
    GetModelJobRequest, GetModelJobGroupRequest, InformModelJobGroupRequest, InformTrustedJobRequest, \
    GetTrustedJobRequest, GetTrustedJobResponse, CreateTrustedExportJobRequest, UpdateDatasetJobSchedulerStateRequest, \
    UpdateModelJobGroupRequest, InformModelJobRequest
from fedlearner_webconsole.review.common import NO_CENTRAL_SERVER_UUID


class FakeContext:

    def __init__(self, metadata):
        self._metadata = metadata

    def invocation_metadata(self):
        return self._metadata


class GetGrpcContextInfoTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='proj-name')
            participant = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            session.add_all([project, participant])
            session.commit()

    def test_get_grpc_context_info(self):
        metadata = ((SSL_CLIENT_SUBJECT_DN_HEADER,
                     'CN=domain2.fedlearner.net,OU=security,O=security,L=beijing,ST=beijing,C=CN'),
                    (PROJECT_NAME_HEADER, 'proj-name'))
        # since interceptor has already validated the info, only test happy case
        with db.session_scope() as session:
            project_id, client_id = get_grpc_context_info(session, FakeContext(metadata))
            self.assertEqual(project_id, 1)
            self.assertEqual(client_id, 1)


class SystemServiceTest(NoWebServerTestCase):
    LISTEN_PORT = 2000

    def setUp(self):
        super().setUp()
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        job_service_pb2_grpc.add_JobServiceServicer_to_server(JobServiceServicer(), self._server)
        self._server.add_insecure_port(f'[::]:{self.LISTEN_PORT}')
        self._server.start()
        self._channel = grpc.insecure_channel(target=f'localhost:{self.LISTEN_PORT}')
        self._stub = job_service_pb2_grpc.JobServiceStub(self._channel)

    def tearDown(self):
        self._channel.close()
        self._server.stop(5)
        return super().tearDown()

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_inform_trusted_job_group(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            project = Project(id=1, name='proj-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
            group = TrustedJobGroup(id=1, name='group', uuid='uuid', project_id=1, coordinator_id=0)
            group.set_unauth_participant_ids([1, 2])
            session.add_all([project, participant1, participant2, group])
            session.commit()
        # authorize
        self._stub.InformTrustedJobGroup(InformTrustedJobGroupRequest(uuid='uuid', auth_status='AUTHORIZED'))
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).filter_by(uuid='uuid').first()
            self.assertCountEqual(group.get_unauth_participant_ids(), [2])
        # pend
        self._stub.InformTrustedJobGroup(InformTrustedJobGroupRequest(uuid='uuid', auth_status='PENDING'))
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).filter_by(uuid='uuid').first()
            self.assertCountEqual(group.get_unauth_participant_ids(), [1, 2])
        # fail due to group uuid not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformTrustedJobGroup(InformTrustedJobGroupRequest(uuid='not-exist', auth_status='AUTHORIZED'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        # fail due to invalid auth status
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformTrustedJobGroup(InformTrustedJobGroupRequest(uuid='uuid', auth_status='AUTHORIZE'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_update_trusted_job_group(self, mock_get_grpc_context_info: MagicMock, mock_get_algorithm: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        mock_get_algorithm.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'not found')
        with db.session_scope() as session:
            project = Project(id=1, name='proj-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            algorithm_proj1 = AlgorithmProject(id=1, uuid='algorithm-proj-uuid1')
            algorithm_proj2 = AlgorithmProject(id=2, uuid='algorithm-proj-uuid2')
            algorithm1 = Algorithm(id=1, algorithm_project_id=1, uuid='algorithm-uuid1')
            algorithm2 = Algorithm(id=2, algorithm_project_id=1, uuid='algorithm-uuid2')
            algorithm3 = Algorithm(id=3, algorithm_project_id=2, uuid='algorithm-uuid3')
            group1 = TrustedJobGroup(id=1,
                                     name='group1',
                                     uuid='uuid1',
                                     project_id=1,
                                     algorithm_uuid='algorithm-uuid1',
                                     coordinator_id=1)
            group2 = TrustedJobGroup(id=2,
                                     name='group2',
                                     uuid='uuid2',
                                     project_id=1,
                                     algorithm_uuid='algorithm-uuid1',
                                     coordinator_id=0)
            session.add_all([
                project, participant1, algorithm_proj1, algorithm_proj2, algorithm1, algorithm2, algorithm3, group1,
                group2
            ])
            session.commit()
        self._stub.UpdateTrustedJobGroup(UpdateTrustedJobGroupRequest(uuid='uuid1', algorithm_uuid='algorithm-uuid2'))
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).filter_by(uuid='uuid1').first()
            self.assertEqual(group.algorithm_uuid, 'algorithm-uuid2')
        # fail due to group uuid not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateTrustedJobGroup(
                UpdateTrustedJobGroupRequest(uuid='not-exist', algorithm_uuid='algorithm-uuid2'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        # fail due to client not coordinator
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateTrustedJobGroup(
                UpdateTrustedJobGroupRequest(uuid='uuid2', algorithm_uuid='algorithm-uuid2'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
        #  fail due to algorithm not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateTrustedJobGroup(
                UpdateTrustedJobGroupRequest(uuid='uuid1', algorithm_uuid='algorithm-not-exist'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        # fail due to mismatched algorithm project
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateTrustedJobGroup(
                UpdateTrustedJobGroupRequest(uuid='uuid1', algorithm_uuid='algorithm-uuid3'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_delete_trusted_job_group(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            project = Project(id=1, name='proj-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            group1 = TrustedJobGroup(id=1, uuid='uuid1', project_id=1, coordinator_id=1)
            group2 = TrustedJobGroup(id=2, uuid='uuid2', project_id=1, coordinator_id=0)
            trusted_job1 = TrustedJob(id=1,
                                      name='V1',
                                      trusted_job_group_id=1,
                                      job_id=1,
                                      status=TrustedJobStatus.RUNNING)
            job1 = Job(id=1, name='job-name1', job_type=JobType.CUSTOMIZED, workflow_id=0, project_id=1)
            trusted_job2 = TrustedJob(id=2,
                                      name='V2',
                                      trusted_job_group_id=1,
                                      job_id=2,
                                      status=TrustedJobStatus.SUCCEEDED)
            job2 = Job(id=2, name='job-name2', job_type=JobType.CUSTOMIZED, workflow_id=0, project_id=1)
            session.add_all([project, participant1, group1, group2, trusted_job1, job1, trusted_job2, job2])
            session.commit()
        # fail due to client is not coordinator
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.DeleteTrustedJobGroup(DeleteTrustedJobGroupRequest(uuid='uuid2'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
        # delete group not exist
        resp = self._stub.DeleteTrustedJobGroup(DeleteTrustedJobGroupRequest(uuid='not-exist'))
        self.assertEqual(resp, Empty())
        # fail due to trusted job is still running
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.DeleteTrustedJobGroup(DeleteTrustedJobGroupRequest(uuid='uuid1'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.FAILED_PRECONDITION)
        # successful
        with db.session_scope() as session:
            trusted_job1 = session.query(TrustedJob).get(1)
            trusted_job1.status = TrustedJobStatus.FAILED
            session.commit()
        self._stub.DeleteTrustedJobGroup(DeleteTrustedJobGroupRequest(uuid='uuid1'))
        with db.session_scope() as session:
            self.assertIsNone(session.query(TrustedJobGroup).get(1))
            self.assertIsNone(session.query(TrustedJob).get(1))
            self.assertIsNone(session.query(TrustedJob).get(2))
            self.assertIsNone(session.query(Job).get(1))
            self.assertIsNone(session.query(Job).get(2))

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_get_trusted_job_group(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            group = TrustedJobGroup(id=1, name='group', uuid='uuid', project_id=1, auth_status=AuthStatus.AUTHORIZED)
            session.add_all([group])
            session.commit()
        resp = self._stub.GetTrustedJobGroup(GetTrustedJobGroupRequest(uuid='uuid'))
        self.assertEqual(resp, GetTrustedJobGroupResponse(auth_status='AUTHORIZED'))
        # fail due to not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.GetTrustedJobGroup(GetTrustedJobGroupRequest(uuid='uuid-not-exist'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_create_trusted_export_job(self, mock_get_grpc_context_info: MagicMock, mock_get_system_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            proj_part2 = ProjectParticipant(project_id=1, participant_id=2)
            tee_analyze_job = TrustedJob(id=1,
                                         uuid='uuid1',
                                         type=TrustedJobType.ANALYZE,
                                         project_id=1,
                                         version=1,
                                         trusted_job_group_id=1,
                                         export_count=2,
                                         status=TrustedJobStatus.SUCCEEDED)
            session.add_all([project, participant1, participant2, proj_part1, proj_part2, tee_analyze_job])
            session.commit()
        # successful
        req = CreateTrustedExportJobRequest(uuid='uuid2',
                                            name='V1-domain2-1',
                                            export_count=1,
                                            ticket_uuid=NO_CENTRAL_SERVER_UUID,
                                            parent_uuid='uuid1')
        self._stub.CreateTrustedExportJob(req)
        with db.session_scope() as session:
            tee_export_job = session.query(TrustedJob).filter_by(uuid='uuid2').first()
            self.assertEqual(tee_export_job.name, 'V1-domain2-1')
            self.assertEqual(tee_export_job.type, TrustedJobType.EXPORT)
            self.assertEqual(tee_export_job.export_count, 1)
            self.assertEqual(tee_export_job.project_id, 1)
            self.assertEqual(tee_export_job.trusted_job_group_id, 1)
            self.assertEqual(tee_export_job.status, TrustedJobStatus.CREATED)
            self.assertEqual(tee_export_job.auth_status, AuthStatus.PENDING)
            participants_info = ParticipantsInfo()
            participants_info.participants_map['domain1'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['domain2'].auth_status = AuthStatus.AUTHORIZED.name
            participants_info.participants_map['domain3'].auth_status = AuthStatus.PENDING.name
            self.assertEqual(tee_export_job.get_participants_info(), participants_info)
        # failed due to tee_analyze_job not valid
        with self.assertRaises(grpc.RpcError) as cm:
            req.parent_uuid = 'not-exist'
            self._stub.CreateTrustedExportJob(req)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        # failed due to ticket invalid
        with self.assertRaises(grpc.RpcError) as cm:
            req.ticket_uuid = 'invalid ticket'
            self._stub.CreateTrustedExportJob(req)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)

    @patch('fedlearner_webconsole.mmgr.service.ModelJobService.create_model_job')
    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_create_model_job(self, mock_get_grpc_context_info: MagicMock, mock_create_model_job: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        # fail due to group not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.CreateModelJob(CreateModelJobRequest(group_uuid='uuid-not-exist'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        with db.session_scope() as session:
            session.add(ModelJobGroup(id=2, name='name', uuid='group_uuid', project_id=1, latest_version=2))
            session.add(ModelJob(id=1, name='model-job', project_id=1))
            session.commit()
        # fail due to model job name already exists
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.CreateModelJob(CreateModelJobRequest(group_uuid='group_uuid', uuid='uuid', name='model-job'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        # fail due to the model job version not larger than group's latest version
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.CreateModelJob(
                CreateModelJobRequest(group_uuid='group_uuid',
                                      name='name',
                                      version=2,
                                      model_job_type=ModelJobType.TRAINING.name,
                                      algorithm_type=AlgorithmType.NN_VERTICAL.name))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        # create training model job successfully
        mock_create_model_job.return_value = ModelJob(name='haha', uuid='uuid', version=3)
        global_config = ModelJobGlobalConfig(global_config={'test': ModelJobConfig()})
        self._stub.CreateModelJob(
            CreateModelJobRequest(name='name',
                                  uuid='uuid',
                                  group_uuid='group_uuid',
                                  model_job_type='TRAINING',
                                  algorithm_type='NN_VERTICAL',
                                  global_config=global_config,
                                  version=3))
        mock_create_model_job.assert_called_with(name='name',
                                                 uuid='uuid',
                                                 group_id=2,
                                                 project_id=1,
                                                 role=ModelJobRole.PARTICIPANT,
                                                 model_job_type=ModelJobType.TRAINING,
                                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                                 coordinator_id=1,
                                                 data_batch_id=None,
                                                 global_config=global_config,
                                                 version=3)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(name='name').first()
            self.assertEqual(group.latest_version, 3)
        # create evaluation model job successfully
        mock_create_model_job.return_value = ModelJob(name='haha', uuid='uuid', version=None)
        global_config = ModelJobGlobalConfig(global_config={'test': ModelJobConfig()})
        self._stub.CreateModelJob(
            CreateModelJobRequest(name='name',
                                  uuid='uuid',
                                  group_uuid='group_uuid',
                                  model_job_type='EVALUATION',
                                  algorithm_type='NN_VERTICAL',
                                  global_config=global_config,
                                  version=0))
        mock_create_model_job.assert_called_with(name='name',
                                                 uuid='uuid',
                                                 group_id=2,
                                                 project_id=1,
                                                 role=ModelJobRole.PARTICIPANT,
                                                 model_job_type=ModelJobType.EVALUATION,
                                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                                 coordinator_id=1,
                                                 data_batch_id=None,
                                                 global_config=global_config,
                                                 version=0)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(name='name').first()
            self.assertEqual(group.latest_version, 3)
        # create auto update model job
        with db.session_scope() as session:
            data_batch = DataBatch(id=1,
                                   name='0',
                                   dataset_id=1,
                                   path='/test_dataset/1/batch/0',
                                   event_time=datetime(2021, 10, 28, 16, 37, 37))
            dataset_job_stage = DatasetJobStage(id=1,
                                                name='data-join',
                                                uuid='dataset-job-stage-uuid',
                                                project_id=1,
                                                state=DatasetJobState.SUCCEEDED,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            session.add_all([data_batch, dataset_job_stage])
            session.commit()
        global_config = ModelJobGlobalConfig(dataset_job_stage_uuid='dataset-job-stage-uuid')
        self._stub.CreateModelJob(
            CreateModelJobRequest(name='name',
                                  uuid='uuid',
                                  group_uuid='group_uuid',
                                  model_job_type='TRAINING',
                                  algorithm_type='NN_VERTICAL',
                                  global_config=global_config,
                                  version=4))
        mock_create_model_job.assert_called_with(name='name',
                                                 uuid='uuid',
                                                 group_id=2,
                                                 project_id=1,
                                                 role=ModelJobRole.PARTICIPANT,
                                                 model_job_type=ModelJobType.TRAINING,
                                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                                 coordinator_id=1,
                                                 data_batch_id=1,
                                                 global_config=global_config,
                                                 version=4)

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_inform_model_job(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='part1', domain_name='fl-demo1.com')
            pro_part = ProjectParticipant(id=1, project_id=1, participant_id=1)
            model_job = ModelJob(id=1,
                                 name='model_job',
                                 uuid='uuid',
                                 project_id=1,
                                 auth_status=ModelAuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo()
            participants_info.participants_map['demo1'].auth_status = AuthStatus.PENDING.name
            model_job.set_participants_info(participants_info)
            session.add_all([project, participant, pro_part, model_job])
            session.commit()
        self._stub.InformModelJob(InformModelJobRequest(uuid='uuid', auth_status=AuthStatus.AUTHORIZED.name))
        # authorized
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            participants_info = model_job.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.AUTHORIZED.name)
        # pending
        self._stub.InformModelJob(InformModelJobRequest(uuid='uuid', auth_status=AuthStatus.PENDING.name))
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            participants_info = model_job.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.PENDING.name)
        # fail due to model job not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformModelJob(InformModelJobRequest(uuid='uuid1', auth_status=AuthStatus.PENDING.name))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        # fail due to auth_status invalid
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformModelJob(InformModelJobRequest(uuid='uuid', auth_status='aaaaa'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    @patch('fedlearner_webconsole.dataset.models.DataBatch.is_available')
    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_create_dataset_job_stage(self, mock_get_grpc_context_info: MagicMock, mock_is_available: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        mock_is_available.return_value = True
        # test streaming
        event_time = datetime(2022, 1, 1)
        request = CreateDatasetJobStageRequest(dataset_job_uuid='dataset_job_123',
                                               dataset_job_stage_uuid='dataset_job_stage_123',
                                               name='test_stage',
                                               event_time=to_timestamp(event_time))
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.CreateDatasetJobStage(request)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertEqual(cm.exception.details(), 'dataset_job dataset_job_123 is not found')
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job_123',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING,
                                     coordinator_id=1)
            session.add(dataset_job)
            dataset = Dataset(id=1,
                              uuid='dataset input',
                              name='default dataset input',
                              dataset_type=DatasetType.PSI,
                              comment='test comment',
                              path='/data/dataset/123',
                              project_id=1,
                              dataset_kind=DatasetKindV2.RAW,
                              is_published=True)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='test_batch',
                                   dataset_id=1,
                                   latest_parent_dataset_job_stage_id=100,
                                   latest_analyzer_dataset_job_stage_id=100)
            session.add(data_batch)
            session.commit()
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.CreateDatasetJobStage(request)
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertEqual(cm.exception.details(), 'output dataset is not found, dataset_job uuid: dataset_job_123')
        with db.session_scope() as session:
            default_dataset = Dataset(id=10,
                                      uuid='dataset_123',
                                      name='default dataset',
                                      dataset_type=DatasetType.STREAMING,
                                      comment='test comment',
                                      path='/data/dataset/123',
                                      project_id=1,
                                      dataset_kind=DatasetKindV2.RAW,
                                      is_published=True)
            session.add(default_dataset)
            session.commit()
        resp = self._stub.CreateDatasetJobStage(request)
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).filter(DataBatch.event_time == event_time).first()
            self.assertEqual(data_batch.dataset_id, 10)
            self.assertEqual(data_batch.name, '20220101')
            self.assertEqual(data_batch.path, '/data/dataset/123/batch/20220101')
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).filter(
                DatasetJobStage.uuid == 'dataset_job_stage_123').first()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.data_batch_id, data_batch.id)
            self.assertEqual(dataset_job_stage.event_time, event_time)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)
        # idempotent test
        resp = self._stub.CreateDatasetJobStage(request)
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            data_batches = session.query(DataBatch).filter(DataBatch.event_time == event_time).all()
            self.assertEqual(len(data_batches), 1)
        # test psi
        with db.session_scope() as session:
            dataset_job_2 = DatasetJob(id=2,
                                       uuid='dataset_job_2',
                                       project_id=1,
                                       input_dataset_id=1,
                                       output_dataset_id=11,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=1)
            session.add(dataset_job_2)
            dataset_2 = Dataset(id=11,
                                uuid='dataset_2',
                                name='default dataset',
                                dataset_type=DatasetType.PSI,
                                comment='test comment',
                                path='/data/dataset/123',
                                project_id=1,
                                dataset_kind=DatasetKindV2.RAW,
                                is_published=True)
            session.add(dataset_2)
            session.commit()
        request = CreateDatasetJobStageRequest(dataset_job_uuid='dataset_job_2',
                                               dataset_job_stage_uuid='dataset_job_stage_2',
                                               name='test_stage')
        resp = self._stub.CreateDatasetJobStage(request)
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).filter(DataBatch.dataset_id == 11).first()
            self.assertEqual(data_batch.name, '0')
            self.assertEqual(data_batch.path, '/data/dataset/123/batch/0')
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).filter(
                DatasetJobStage.uuid == 'dataset_job_stage_2').first()
            self.assertEqual(dataset_job_stage.dataset_job_id, 2)
            self.assertEqual(dataset_job_stage.data_batch_id, data_batch.id)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)
        # idempotent test
        resp = self._stub.CreateDatasetJobStage(request)
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            data_batches = session.query(DataBatch).filter(DataBatch.dataset_id == 11).all()
            self.assertEqual(len(data_batches), 1)

        # test batch not ready
        mock_is_available.reset_mock()
        mock_is_available.return_value = False
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.CreateDatasetJobStage(request)
            self.assertEqual(cm.exception.code(), grpc.StatusCode.FAILED_PRECONDITION)

    @patch('fedlearner_webconsole.dataset.services.DatasetJobConfiger.from_kind',
           lambda *args: FakeDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_get_dataset_job_stage(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job_uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=0,
                                     kind=DatasetJobKind.IMPORT_SOURCE,
                                     state=DatasetJobState.RUNNING,
                                     coordinator_id=0,
                                     workflow_id=0)
            session.add(dataset_job)
            job_stage = DatasetJobStage(id=1,
                                        uuid='job_stage_uuid',
                                        name='default dataset job stage',
                                        project_id=1,
                                        workflow_id=1,
                                        dataset_job_id=1,
                                        data_batch_id=1,
                                        event_time=datetime(2012, 1, 15),
                                        state=DatasetJobState.PENDING)
            session.add(job_stage)
            session.commit()
        request = GetDatasetJobStageRequest(dataset_job_stage_uuid='job_stage_uuid')
        resp = self._stub.GetDatasetJobStage(request)
        self.assertEqual(resp.dataset_job_stage.uuid, 'job_stage_uuid')
        self.assertEqual(resp.dataset_job_stage.name, 'default dataset job stage')
        self.assertEqual(resp.dataset_job_stage.dataset_job_id, 1)
        self.assertEqual(resp.dataset_job_stage.event_time, to_timestamp(datetime(2012, 1, 15)))
        self.assertEqual(resp.dataset_job_stage.is_ready, False)

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_update_dataset_job_scheduler_state(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job_uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=0,
                                     kind=DatasetJobKind.IMPORT_SOURCE,
                                     state=DatasetJobState.RUNNING,
                                     coordinator_id=0,
                                     workflow_id=0,
                                     scheduler_state=DatasetJobSchedulerState.PENDING,
                                     time_range=timedelta(days=1))
            session.add(dataset_job)
            session.commit()
        request = UpdateDatasetJobSchedulerStateRequest(uuid='dataset_job_uuid',
                                                        scheduler_state=DatasetJobSchedulerState.RUNNABLE.name)
        resp = self._stub.UpdateDatasetJobSchedulerState(request)
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.RUNNABLE)
        request = UpdateDatasetJobSchedulerStateRequest(uuid='dataset_job_uuid',
                                                        scheduler_state=DatasetJobSchedulerState.STOPPED.name)
        resp = self._stub.UpdateDatasetJobSchedulerState(request)
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.STOPPED)
        request = UpdateDatasetJobSchedulerStateRequest(uuid='dataset_job_uuid',
                                                        scheduler_state=DatasetJobSchedulerState.PENDING.name)
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateDatasetJobSchedulerState(request)

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_get_model_job(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        request = GetModelJobRequest(uuid='uuid')
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.GetModelJob(request=request)
            self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
            self.assertEqual(cm.exception.details(), 'model job uuid is not found')
        with db.session_scope() as session:
            model_job = ModelJob(uuid='uuid',
                                 role=ModelJobRole.PARTICIPANT,
                                 model_job_type=ModelJobType.TRAINING,
                                 algorithm_type=AlgorithmType.NN_VERTICAL,
                                 auth_status=ModelAuthStatus.AUTHORIZED,
                                 status=ModelJobStatus.CONFIGURED,
                                 created_at=datetime(2022, 8, 16, 0, 0),
                                 updated_at=datetime(2022, 8, 16, 0, 0))
            session.add(model_job)
            session.commit()
        resp = self._stub.GetModelJob(request=request)
        self.assertEqual(
            resp,
            ModelJobPb(id=1,
                       uuid='uuid',
                       role='PARTICIPANT',
                       model_job_type='TRAINING',
                       algorithm_type='NN_VERTICAL',
                       state='PENDING_ACCEPT',
                       auth_status='AUTHORIZED',
                       status='CONFIGURED',
                       auth_frontend_status='ALL_AUTHORIZED',
                       participants_info=ParticipantsInfo(),
                       created_at=1660608000,
                       updated_at=1660608000))

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_get_model_job_group(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        request = GetModelJobGroupRequest(uuid='uuid')
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.GetModelJobGroup(request=request)
            self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
            self.assertEqual(cm.exception.details(), 'model job group with uuid uuid is not found')
        with db.session_scope() as session:
            group = ModelJobGroup(id=1,
                                  role=ModelJobRole.PARTICIPANT,
                                  uuid='uuid',
                                  authorized=True,
                                  algorithm_type=AlgorithmType.NN_VERTICAL,
                                  created_at=datetime(2022, 8, 16, 0, 0),
                                  updated_at=datetime(2022, 8, 16, 0, 0))
            session.add(group)
            session.commit()
        resp = self._stub.GetModelJobGroup(request=request)
        self.assertEqual(
            resp,
            ModelJobGroupPb(id=1,
                            uuid='uuid',
                            role='PARTICIPANT',
                            algorithm_type='NN_VERTICAL',
                            authorized=True,
                            auth_frontend_status='ALL_AUTHORIZED',
                            auth_status='PENDING',
                            auto_update_status='INITIAL',
                            participants_info=ParticipantsInfo(),
                            algorithm_project_uuid_list=AlgorithmProjectList(),
                            created_at=1660608000,
                            updated_at=1660608000))

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_inform_model_job_group(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part1', domain_name='fl-demo1.com')
            participant2 = Participant(id=2, name='part2', domain_name='fl-demo2.com')
            group = ModelJobGroup(id=1, uuid='uuid', project_id=1)
            participants_info = ParticipantsInfo()
            participants_info.participants_map['demo1'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['demo2'].auth_status = AuthStatus.PENDING.name
            group.set_participants_info(participants_info)
            session.add_all([project, participant1, participant2, group])
            session.commit()
        # authorized
        self._stub.InformModelJobGroup(InformModelJobGroupRequest(uuid='uuid', auth_status=AuthStatus.AUTHORIZED.name))
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.AUTHORIZED.name)
        # pending
        self._stub.InformModelJobGroup(InformModelJobGroupRequest(uuid='uuid', auth_status=AuthStatus.PENDING.name))
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.PENDING.name)
        # fail due to group not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformModelJobGroup(
                InformModelJobGroupRequest(uuid='uuid-1', auth_status=AuthStatus.PENDING.name))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        # fail due to auth_status invalid
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformModelJobGroup(InformModelJobGroupRequest(uuid='uuid', auth_status='aaaaa'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_update_model_job_group(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            group = ModelJobGroup(id=1,
                                  name='group',
                                  uuid='group_uuid',
                                  project_id=1,
                                  auto_update_status=GroupAutoUpdateStatus.INITIAL)
            dataset_job_stage = DatasetJobStage(id=1,
                                                name='data_join',
                                                uuid='stage_uuid',
                                                project_id=1,
                                                state=DatasetJobState.SUCCEEDED,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            session.add_all([project, group, dataset_job_stage])
            session.commit()
        # fail due to group not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateModelJobGroup(
                UpdateModelJobGroupRequest(uuid='uuid',
                                           auto_update_status=GroupAutoUpdateStatus.ACTIVE.name,
                                           start_dataset_job_stage_uuid='stage_uuid'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        # fail due to auto_update_status invalid
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.UpdateModelJobGroup(
                UpdateModelJobGroupRequest(uuid='group_uuid',
                                           auto_update_status='aaa',
                                           start_dataset_job_stage_uuid='stage_uuid'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        # update auto_update_status and start_data_batch_id
        self._stub.UpdateModelJobGroup(
            UpdateModelJobGroupRequest(uuid='group_uuid',
                                       auto_update_status=GroupAutoUpdateStatus.ACTIVE.name,
                                       start_dataset_job_stage_uuid='stage_uuid'))
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(uuid='group_uuid', project_id=1).first()
            self.assertEqual(group.auto_update_status, GroupAutoUpdateStatus.ACTIVE)
            self.assertEqual(group.start_data_batch_id, 1)
        # only update auto_update_status
        self._stub.UpdateModelJobGroup(
            UpdateModelJobGroupRequest(uuid='group_uuid', auto_update_status=GroupAutoUpdateStatus.STOPPED.name))
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(uuid='group_uuid', project_id=1).first()
            self.assertEqual(group.auto_update_status, GroupAutoUpdateStatus.STOPPED)

    @patch('fedlearner_webconsole.mmgr.service.ModelJobGroupService.create_group')
    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_create_model_job_group(self, mock_get_grpc_context_info: MagicMock, mock_create_group: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        request = CreateModelJobGroupRequest(
            name='name',
            uuid='uuid',
            algorithm_type=AlgorithmType.NN_VERTICAL.name,
            dataset_uuid='uuid',
            algorithm_project_list=AlgorithmProjectList(algorithm_projects={'test': 'uuid'}))
        with self.assertRaises(grpc.RpcError) as cm:
            # test dataset not found
            resp = self._stub.CreateModelJobGroup(request)
            self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
            self.assertEqual(cm.exception.details(), 'dataset with uuid uuid is not found')
        with db.session_scope() as session:
            session.add(Dataset(id=1, name='name', uuid='uuid'))
            session.commit()
        mock_create_group.return_value = ModelJobGroup(name='name', uuid='uuid')
        resp = self._stub.CreateModelJobGroup(request)
        # create group
        mock_create_group.assert_called_with(
            name='name',
            uuid='uuid',
            project_id=1,
            role=ModelJobRole.PARTICIPANT,
            dataset_id=1,
            algorithm_type=AlgorithmType.NN_VERTICAL,
            algorithm_project_list=AlgorithmProjectList(algorithm_projects={'test': 'uuid'}),
            coordinator_id=1)
        mock_create_group.reset_mock()
        resp = self._stub.CreateModelJobGroup(request)
        # create group not called if group is already created
        mock_create_group.assert_not_called()

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_inform_trusted_job(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part1', domain_name='fl-domain2.com')
            trusted_job = TrustedJob(id=1, uuid='uuid', project_id=1)
            participants_info = ParticipantsInfo()
            participants_info.participants_map['domain2'].auth_status = AuthStatus.PENDING.name
            trusted_job.set_participants_info(participants_info)
            session.add_all([project, participant1, trusted_job])
            session.commit()
        self._stub.InformTrustedJob(InformTrustedJobRequest(uuid='uuid', auth_status=AuthStatus.AUTHORIZED.name))
        with db.session_scope() as session:
            trusted_job = session.query(TrustedJob).get(1)
            participants_info = trusted_job.get_participants_info()
            self.assertEqual(participants_info.participants_map['domain2'].auth_status, AuthStatus.AUTHORIZED.name)
        # fail due to group not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformTrustedJob(InformTrustedJobRequest(uuid='not-exist', auth_status=AuthStatus.WITHDRAW.name))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
        # fail due to auth_status invalid
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.InformTrustedJob(InformTrustedJobRequest(uuid='uuid', auth_status='AUTHORIZE'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    @patch('fedlearner_webconsole.rpc.v2.job_service_server.get_grpc_context_info')
    def test_get_trusted_job(self, mock_get_grpc_context_info: MagicMock):
        mock_get_grpc_context_info.return_value = 1, 1
        with db.session_scope() as session:
            trusted_job = TrustedJob(id=1, name='name', uuid='uuid', project_id=1, auth_status=AuthStatus.AUTHORIZED)
            session.add_all([trusted_job])
            session.commit()
        resp = self._stub.GetTrustedJob(GetTrustedJobRequest(uuid='uuid'))
        self.assertEqual(resp, GetTrustedJobResponse(auth_status='AUTHORIZED'))
        # fail due to not found
        with self.assertRaises(grpc.RpcError) as cm:
            self._stub.GetTrustedJob(GetTrustedJobRequest(uuid='uuid-not-exist'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)


if __name__ == '__main__':
    unittest.main()
