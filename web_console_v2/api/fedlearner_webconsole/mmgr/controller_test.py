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
from unittest.mock import MagicMock, patch, call

import grpc
from google.protobuf import json_format
from google.protobuf.empty_pb2 import Empty
from datetime import datetime
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.fake_model_job_config import get_workflow_config
from testing.rpc.client import FakeRpcError

from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmType, Source
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobState, DatasetJobKind, DatasetType, \
    DatasetJobStage, DataBatch
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobGroup, ModelJobType, ModelJobRole, GroupCreateStatus, \
    GroupAutoUpdateStatus, AuthStatus as ModelJobAuthStatus
from fedlearner_webconsole.mmgr.controller import start_model_job, stop_model_job, ModelJobGroupController, \
    ModelJobController
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmPb
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGroupPb, AlgorithmProjectList, ModelJobPb
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.workflow_template.utils import set_value
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus


class StartModelJobTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            session.add(ModelJob(id=1, name='name', uuid='uuid', workflow_id=2))
            session.commit()

    @patch('fedlearner_webconsole.mmgr.controller.start_workflow')
    def test_start_model_job(self, mock_start_workflow: MagicMock):
        start_model_job(model_job_id=1)
        mock_start_workflow.assert_called_with(workflow_id=2)

    @patch('fedlearner_webconsole.mmgr.controller.stop_workflow')
    def test_stop_model_job(self, mock_stop_workflow: MagicMock):
        stop_model_job(model_job_id=1)
        mock_stop_workflow.assert_called_with(workflow_id=2)


class ModelJobGroupControllerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part1', domain_name='fl-demo1.com')
            participant2 = Participant(id=2, name='part2', domain_name='fl-demo2.com')
            dataset = Dataset(id=1, name='dataset', uuid='dataset_uuid')
            pro_part1 = ProjectParticipant(id=1, project_id=1, participant_id=1)
            pro_part2 = ProjectParticipant(id=2, project_id=1, participant_id=2)
            group = ModelJobGroup(id=1,
                                  name='group',
                                  uuid='uuid',
                                  project_id=1,
                                  dataset_id=1,
                                  algorithm_type=AlgorithmType.NN_VERTICAL)
            dataset_job_stage = DatasetJobStage(id=1,
                                                name='data_join',
                                                uuid='stage_uuid',
                                                project_id=1,
                                                state=DatasetJobState.SUCCEEDED,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            data_batch = DataBatch(id=1,
                                   name='20221213',
                                   dataset_id=1,
                                   path='/data/dataset/haha/batch/20221213',
                                   latest_parent_dataset_job_stage_id=1,
                                   event_time=datetime(2022, 12, 13, 16, 37, 37))
            algorithm_project_list = AlgorithmProjectList()
            algorithm_project_list.algorithm_projects['test'] = 'algorithm-project-uuid1'
            algorithm_project_list.algorithm_projects['part1'] = 'algorithm-project-uuid2'
            algorithm_project_list.algorithm_projects['part2'] = 'algorithm-project-uuid3'
            group.set_algorithm_project_uuid_list(algorithm_project_list)
            algo = Algorithm(id=1, algorithm_project_id=1, name='test-algo', uuid='uuid')
            participants_info = ParticipantsInfo()
            participants_info.participants_map['demo0'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['demo1'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['demo2'].auth_status = AuthStatus.PENDING.name
            group.set_participants_info(participants_info)
            session.add_all([
                project, participant1, participant2, pro_part1, pro_part2, group, algo, dataset, dataset_job_stage,
                data_batch
            ])
            session.commit()

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_model_job_group')
    def test_inform_auth_status_to_participants(self, mock_client: MagicMock, mock_system_info: MagicMock):
        system_info = SystemInfo()
        system_info.pure_domain_name = 'demo0'
        mock_system_info.return_value = system_info
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            group.auth_status = AuthStatus.AUTHORIZED
            ModelJobGroupController(session, 1).inform_auth_status_to_participants(group)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map[system_info.pure_domain_name].auth_status,
                             AuthStatus.AUTHORIZED.name)
            self.assertEqual(mock_client.call_args_list, [(('uuid', AuthStatus.AUTHORIZED),),
                                                          (('uuid', AuthStatus.AUTHORIZED),)])
        # fail due to grpc abort
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'model job group uuid is not found')
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            group.auth_status = AuthStatus.PENDING
            ModelJobGroupController(session, 1).inform_auth_status_to_participants(group)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map[system_info.pure_domain_name].auth_status,
                             AuthStatus.PENDING.name)

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.update_model_job_group')
    def test_update_participants_model_job_group(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            group.auto_update_status = GroupAutoUpdateStatus.ACTIVE
            group.start_data_batch_id = 1
            ModelJobGroupController(session, 1).update_participants_model_job_group(
                uuid=group.uuid,
                auto_update_status=group.auto_update_status,
                start_data_batch_id=group.start_data_batch_id)
            self.assertEqual(mock_client.call_args_list, [
                call(uuid='uuid',
                     auto_update_status=GroupAutoUpdateStatus.ACTIVE,
                     start_dataset_job_stage_uuid='stage_uuid'),
                call(uuid='uuid',
                     auto_update_status=GroupAutoUpdateStatus.ACTIVE,
                     start_dataset_job_stage_uuid='stage_uuid')
            ])

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_model_job_group')
    def test_update_participants_auth_status(self, mock_client: MagicMock):
        mock_client.side_effect = [
            ModelJobGroupPb(auth_status=AuthStatus.AUTHORIZED.name),
            ModelJobGroupPb(auth_status=AuthStatus.AUTHORIZED.name)
        ]
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            ModelJobGroupController(session, 1).update_participants_auth_status(group)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.AUTHORIZED.name)
            self.assertEqual(participants_info.participants_map['demo2'].auth_status, AuthStatus.AUTHORIZED.name)
        # if the 'auth_status' is not in ModelJobGroupPb
        mock_client.side_effect = [ModelJobGroupPb(authorized=False), ModelJobGroupPb(authorized=False)]
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            ModelJobGroupController(session, 1).update_participants_auth_status(group)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.PENDING.name)
            self.assertEqual(participants_info.participants_map['demo2'].auth_status, AuthStatus.PENDING.name)
        # fail due to grpc abort
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'model job group uuid is not found')
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            ModelJobGroupController(session, 1).update_participants_auth_status(group)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map['demo1'].auth_status, AuthStatus.PENDING.name)
            self.assertEqual(participants_info.participants_map['demo2'].auth_status, AuthStatus.PENDING.name)

    @patch('fedlearner_webconsole.rpc.v2.system_service_client.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_model_job_group')
    def test_get_model_job_group_from_participant(self, mock_client: MagicMock, mock_algo_fetcher: MagicMock,
                                                  mock_list_flags: MagicMock):
        algo_dict1 = {
            'algorithmId': 1,
            'algorithmUuid': 'uuid',
            'algorithmProjectId': 1,
            'algorithmProjectUuid': 'project_uuid',
            'participantId': 0,
            'path': '/path'
        }
        variable = Variable(name='algorithm')
        set_value(variable=variable, typed_value=algo_dict1)
        config = WorkflowDefinition(job_definitions=[JobDefinition(variables=[variable])])
        mock_client.return_value = ModelJobGroupPb(name='group', uuid='uuid', config=config)
        mock_list_flags.return_value = {'model_job_global_config_enabled': True}
        with db.session_scope() as session:
            resp = ModelJobGroupController(session, 1).get_model_job_group_from_participant(1, 'uuid')
            self.assertEqual(resp.name, 'group')
            self.assertEqual(resp.uuid, 'uuid')
            variables = resp.config.job_definitions[0].variables
            for variable in variables:
                if variable.name == 'algorithm':
                    self.assertEqual(json_format.MessageToDict(variable.typed_value), algo_dict1)
        algo_dict2 = {
            'algorithmId': 2,
            'algorithmUuid': 'peer-uuid',
            'algorithmProjectId': 1,
            'algorithmProjectUuid': 'project_uuid',
            'participantId': 2,
            'path': '/path'
        }
        set_value(variable, typed_value=algo_dict2)
        config = WorkflowDefinition(job_definitions=[JobDefinition(variables=[variable])])
        mock_client.return_value = ModelJobGroupPb(name='group', uuid='uuid', config=config)
        mock_algo_fetcher.return_value = AlgorithmPb(name='test-peer-algo',
                                                     uuid='peer-uuid',
                                                     participant_id=1,
                                                     source=Source.PARTICIPANT.name)
        with db.session_scope() as session:
            resp = ModelJobGroupController(session, 1).get_model_job_group_from_participant(1, 'uuid')
            variables = resp.config.job_definitions[0].variables
            algo_dict2['algorithmId'] = 0
            algo_dict2['algorithmProjectId'] = 0
            algo_dict2['participantId'] = 1
            for variable in variables:
                if variable.name == 'algorithm':
                    self.assertEqual(json_format.MessageToDict(variable.typed_value), algo_dict2)

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job_group')
    def test_create_model_job_group_for_participants(self, mock_client: MagicMock):
        with db.session_scope() as session:
            ModelJobGroupController(session, 1).create_model_job_group_for_participants(1)
            session.commit()
        algorithm_project_list = AlgorithmProjectList()
        algorithm_project_list.algorithm_projects['test'] = 'algorithm-project-uuid1'
        algorithm_project_list.algorithm_projects['part1'] = 'algorithm-project-uuid2'
        algorithm_project_list.algorithm_projects['part2'] = 'algorithm-project-uuid3'
        mock_client.assert_called_with(name='group',
                                       uuid='uuid',
                                       algorithm_type=AlgorithmType.NN_VERTICAL,
                                       dataset_uuid='dataset_uuid',
                                       algorithm_project_list=algorithm_project_list)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            self.assertEqual(group.status, GroupCreateStatus.SUCCEEDED)
        mock_client.side_effect = FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, 'dataset with uuid is not found')
        with db.session_scope() as session:
            ModelJobGroupController(session, 1).create_model_job_group_for_participants(1)
            session.commit()
        mock_client.assert_called()
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            self.assertEqual(group.status, GroupCreateStatus.FAILED)


class ModelJobControllerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            project = Project(id=1, name='test-project')
            participant1 = Participant(id=1, name='part1', domain_name='fl-demo1.com')
            participant2 = Participant(id=2, name='part2', domain_name='fl-demo2.com')
            pro_part1 = ProjectParticipant(id=1, project_id=1, participant_id=1)
            pro_part2 = ProjectParticipant(id=2, project_id=1, participant_id=2)
            dataset_job = DatasetJob(id=1,
                                     name='datasetjob',
                                     uuid='uuid',
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=3,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN)
            dataset = Dataset(id=3,
                              uuid='uuid',
                              name='datasetjob',
                              dataset_type=DatasetType.PSI,
                              path='/data/dataset/haha')
            algorithm = Algorithm(id=2, name='algorithm')
            group = ModelJobGroup(id=1,
                                  name='group',
                                  uuid='uuid',
                                  project_id=1,
                                  algorithm_type=AlgorithmType.NN_VERTICAL,
                                  algorithm_id=2,
                                  role=ModelJobRole.COORDINATOR,
                                  dataset_id=3)
            model_job = ModelJob(id=1,
                                 name='model_job',
                                 uuid='uuid',
                                 project_id=1,
                                 auth_status=ModelJobAuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            model_job.set_participants_info(participants_info)
            group.set_config(get_workflow_config(ModelJobType.TRAINING))
            session.add_all([
                dataset_job, dataset, project, group, algorithm, participant1, participant2, pro_part1, pro_part2,
                model_job
            ])
            session.commit()

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_launch_model_job(self, mock_remote_do_two_pc):
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(uuid='uuid').first()
        mock_remote_do_two_pc.return_value = True, ''
        with db.session_scope() as session:
            ModelJobController(session=session, project_id=1).launch_model_job(group_id=1)
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(name='group').first()
            model_job = group.model_jobs[0]
            self.assertEqual(model_job.group_id, group.id)
            self.assertTrue(model_job.project_id, group.project_id)
            self.assertEqual(model_job.version, 1)
            self.assertEqual(group.latest_version, 1)
            self.assertTrue(model_job.algorithm_type, group.algorithm_type)
            self.assertTrue(model_job.model_job_type, ModelJobType.TRAINING)
            self.assertTrue(model_job.dataset_id, group.dataset_id)
            self.assertTrue(model_job.workflow.get_config(), group.get_config())

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_model_job')
    def test_inform_auth_status_to_participants(self, mock_inform_model_job: MagicMock):
        mock_inform_model_job.return_value = Empty()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            ModelJobController(session, 1).inform_auth_status_to_participants(model_job)
            self.assertEqual(mock_inform_model_job.call_args_list, [(('uuid', ModelJobAuthStatus.AUTHORIZED),),
                                                                    (('uuid', ModelJobAuthStatus.AUTHORIZED),)])
        # fail due to grpc abort
        mock_inform_model_job.reset_mock()
        mock_inform_model_job.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'model job uuid is not found')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            ModelJobController(session, 1).inform_auth_status_to_participants(model_job)
            self.assertEqual(mock_inform_model_job.call_args_list, [(('uuid', ModelJobAuthStatus.AUTHORIZED),),
                                                                    (('uuid', ModelJobAuthStatus.AUTHORIZED),)])

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_model_job')
    def test_get_participants_auth_status(self, mock_get_model_job: MagicMock):
        mock_get_model_job.side_effect = [
            ModelJobPb(auth_status=AuthStatus.AUTHORIZED.name),
            ModelJobPb(auth_status=AuthStatus.AUTHORIZED.name)
        ]
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            ModelJobController(session, 1).update_participants_auth_status(model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            self.assertEqual(model_job.get_participants_info(), participants_info)
        # fail due to grpc abort
        mock_get_model_job.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'model job uuid is not found')
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            ModelJobController(session, 1).update_participants_auth_status(model_job)
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            participants_info = ParticipantsInfo(
                participants_map={
                    'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo1': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'demo2': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                })
            self.assertEqual(model_job.get_participants_info(), participants_info)


if __name__ == '__main__':
    unittest.main()
