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
import urllib.parse
from http import HTTPStatus
from datetime import datetime
from unittest.mock import patch, Mock, ANY, MagicMock, call
from google.protobuf.empty_pb2 import Empty
from envs import Envs
from testing.common import BaseTestCase
from testing.fake_model_job_config import get_global_config, get_workflow_config

from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.flask_utils import to_dict
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.participant.models import ProjectParticipant
from fedlearner_webconsole.mmgr.models import ModelJob, ModelJobGroup, ModelJobType, ModelJobRole, \
    GroupAuthFrontendStatus, GroupAutoUpdateStatus, ModelJobStatus
from fedlearner_webconsole.algorithm.models import AlgorithmType, Algorithm, AlgorithmProject
from fedlearner_webconsole.proto.service_pb2 import UpdateModelJobGroupResponse
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGroupPb, AlgorithmProjectList
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus


class ModelJobGroupsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='party', domain_name='fl-peer.com', host='127.0.0.1', port=32443)
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            algo_project = AlgorithmProject(id=1, name='algo')
            algo = Algorithm(id=2, name='algo', algorithm_project_id=1)
            session.add_all([project, algo, algo_project, participant, relationship])
            g1 = ModelJobGroup(id=1,
                               name='g1',
                               uuid='u1',
                               role=ModelJobRole.COORDINATOR,
                               algorithm_type=AlgorithmType.NN_VERTICAL,
                               algorithm_project_id=1,
                               algorithm_id=2,
                               project_id=1,
                               created_at=datetime(2021, 1, 1, 0, 0, 0))
            g1.set_config(get_workflow_config(ModelJobType.TRAINING))
            g2 = ModelJobGroup(name='g2',
                               uuid='u2',
                               project_id=1,
                               role=ModelJobRole.COORDINATOR,
                               algorithm_type=AlgorithmType.NN_HORIZONTAL,
                               created_at=datetime(2021, 1, 1, 0, 0, 1))
            g3 = ModelJobGroup(name='g3',
                               uuid='u3',
                               project_id=2,
                               role=ModelJobRole.PARTICIPANT,
                               algorithm_type=AlgorithmType.TREE_VERTICAL,
                               created_at=datetime(2021, 1, 1, 0, 0, 1))
            workflow = Workflow(id=1, name='workflow', state=WorkflowState.RUNNING)
            model_job = ModelJob(id=1, group_id=1, status=ModelJobStatus.PENDING, workflow_id=1)
            dataset = Dataset(name='dataset', uuid='dataset_uuid', is_published=True)
            session.add_all([g1, g2, g3, dataset, workflow, model_job])
            session.commit()

    def test_get_groups(self):
        resp = self.get_helper('/api/v2/projects/1/model_job_groups')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'g2')
        self.assertEqual(data[0]['configured'], False)
        self.assertEqual(data[1]['name'], 'g1')
        self.assertEqual(data[1]['configured'], True)
        self.assertEqual(data[1]['latest_job_state'], 'RUNNING')
        resp = self.get_helper('/api/v2/projects/0/model_job_groups')
        data = self.get_response_data(resp)
        self.assertEqual(len(data), 3)
        resp = self.get_helper('/api/v2/projects/0/model_job_groups?filter=(configured%3Dfalse)')
        data = self.get_response_data(resp)
        self.assertEqual(sorted([d['name'] for d in data]), ['g2', 'g3'])

    def test_get_groups_by_filtering_expression(self):
        filter_param = urllib.parse.quote('(algorithm_type:["NN_VERTICAL","NN_HORIZONTAL"])')
        resp = self.get_helper(f'/api/v2/projects/0/model_job_groups?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g2', 'g1'])
        filter_param = urllib.parse.quote('(algorithm_type:["NN_VERTICAL"])')
        resp = self.get_helper(f'/api/v2/projects/0/model_job_groups?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g1'])
        filter_param = urllib.parse.quote('(role:["COORDINATOR"])')
        resp = self.get_helper(f'/api/v2/projects/0/model_job_groups?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g2', 'g1'])
        filter_param = urllib.parse.quote('(name~="1")')
        resp = self.get_helper(f'/api/v2/projects/0/model_job_groups?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g1'])
        filter_param = urllib.parse.quote('created_at asc')
        resp = self.get_helper(f'/api/v2/projects/0/model_job_groups?order_by={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g1', 'g2', 'g3'])

    # TODO(linfan): refactor transaction manager
    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    @patch('fedlearner_webconsole.two_pc.model_job_group_creator.ModelJobGroupCreator.prepare')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_post_model_job_group(self, mock_remote_twp_pc, mock_prepare, mock_system_info):
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        mock_prepare.return_value = True, ''
        with db.session_scope() as session:
            dataset_id = session.query(Dataset).filter_by(uuid='dataset_uuid').first().id
        mock_remote_twp_pc.return_value = True, ''
        resp = self.post_helper('/api/v2/projects/1/model_job_groups',
                                data={
                                    'name': 'group',
                                    'algorithm_type': AlgorithmType.NN_VERTICAL.name,
                                    'dataset_id': dataset_id
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(name='group').first()
            self.assertEqual(group.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(group.role, ModelJobRole.COORDINATOR)
            self.assertIsNone(group.coordinator_id)
            self.assertEqual(group.creator_username, 'ada')
            self.assertEqual(
                group.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'peer': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.PART_AUTH_PENDING)

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_post_model_job_group_failed(self, mock_remote_twp_pc):
        mock_remote_twp_pc.return_value = True, ''
        resp = self.post_helper('/api/v2/projects/1/model_job_groups',
                                data={
                                    'name': 'group',
                                    'algorithm_type': AlgorithmType.NN_VERTICAL.name,
                                    'dataset_id': -1
                                })
        # fail due to dataset is not found
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter_by(uuid='dataset_uuid').first()
            dataset.is_published = False
            session.add(dataset)
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/model_job_groups',
                                data={
                                    'name': 'group',
                                    'algorithm_type': AlgorithmType.NN_VERTICAL.name,
                                    'dataset_id': dataset.id
                                })
        # fail due to dataset is not published
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)


class ModelJobGroupsApiV2Test(BaseTestCase):

    def setUp(self):
        super().setUp()
        Envs.SYSTEM_INFO = '{"domain_name": "fl-test.com"}'
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='party', domain_name='fl-peer.com', host='127.0.0.1', port=32443)
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            algo_project = AlgorithmProject(id=1, name='algo')
            algo = Algorithm(id=2, name='algo', algorithm_project_id=1)
            dataset = Dataset(id=1, name='dataset', uuid='dataset_uuid', is_published=True)
            session.add_all([project, algo, algo_project, participant, relationship, dataset])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.create_model_job_group')
    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_post_model_job(self, mock_system_info, mock_client):
        mock_system_info.return_value = SystemInfo(pure_domain_name='test', name='name')
        algorithm_project_list = AlgorithmProjectList()
        algorithm_project_list.algorithm_projects['test'] = 'uuid-test'
        algorithm_project_list.algorithm_projects['peer'] = 'uuid-peer'
        resp = self.post_helper('/api/v2/projects/1/model_job_groups_v2',
                                data={
                                    'name': 'group',
                                    'dataset_id': 1,
                                    'algorithm_type': AlgorithmType.NN_VERTICAL.name,
                                    'algorithm_project_list': to_dict(algorithm_project_list),
                                    'comment': 'comment'
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        mock_client.assert_called()
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(name='group').first()
            self.assertEqual(group.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(group.role, ModelJobRole.COORDINATOR)
            self.assertEqual(group.dataset.uuid, 'dataset_uuid')
            self.assertIsNone(group.coordinator_id)
            self.assertEqual(group.creator_username, 'ada')
            self.assertEqual(group.comment, 'comment')
            self.assertEqual(
                group.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'peer': ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                        'test': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))
            self.assertEqual(group.get_algorithm_project_uuid_list(),
                             AlgorithmProjectList(algorithm_projects={
                                 'peer': 'uuid-peer',
                                 'test': 'uuid-test'
                             }))
            self.assertEqual(group.get_group_auth_frontend_status(), GroupAuthFrontendStatus.PART_AUTH_PENDING)
            self.assertEqual(group.to_proto().configured, True)
        resp = self.post_helper('/api/v2/projects/1/model_job_groups_v2',
                                data={
                                    'name': 'new_group',
                                    'dataset_id': 1,
                                    'algorithm_type': AlgorithmType.TREE_VERTICAL.name,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).filter_by(name='new_group').first()
            self.assertEqual(group.dataset.uuid, 'dataset_uuid')
            algorithm_project_list = AlgorithmProjectList()
            self.assertEqual(group.get_algorithm_project_uuid_list(), algorithm_project_list)
        resp = self.post_helper('/api/v2/projects/1/model_job_groups_v2',
                                data={
                                    'name': 'new_group',
                                    'dataset_id': 1,
                                    'algorithm_type': AlgorithmType.NN_VERTICAL.name,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)


class ModelJobGroupApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Envs.SYSTEM_INFO = '{"domain_name": "fl-test.com"}'
        with db.session_scope() as session:
            algo_project = AlgorithmProject(id=123, name='algo_project', project_id=1)
            dataset = Dataset(id=2, name='dataset')
            algorithm = Algorithm(id=1,
                                  name='algo',
                                  algorithm_project_id=123,
                                  type=AlgorithmType.NN_VERTICAL,
                                  project_id=1)
            group = ModelJobGroup(id=1,
                                  name='group',
                                  algorithm_type=AlgorithmType.NN_VERTICAL,
                                  uuid='uuid',
                                  creator_username='ada',
                                  project_id=1,
                                  created_at=datetime(2022, 5, 6, 0, 0, 0),
                                  updated_at=datetime(2022, 5, 6, 0, 0, 0))
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part1', domain_name='fl-demo1.com')
            participant2 = Participant(id=2, name='part2', domain_name='fl-demo2.com')
            pro_part1 = ProjectParticipant(id=1, project_id=1, participant_id=1)
            pro_part2 = ProjectParticipant(id=2, project_id=1, participant_id=2)
            participants_info = ParticipantsInfo()
            participants_info.participants_map['test'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['demo1'].auth_status = AuthStatus.PENDING.name
            participants_info.participants_map['demo2'].auth_status = AuthStatus.PENDING.name
            group.set_participants_info(participants_info)
            session.add_all(
                [algo_project, algorithm, group, dataset, project, participant1, participant2, pro_part1, pro_part2])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_model_job_group')
    def test_get_group(self, mock_client: MagicMock):
        mock_client.side_effect = [
            ModelJobGroupPb(auth_status=AuthStatus.AUTHORIZED.name),
            ModelJobGroupPb(auth_status=AuthStatus.AUTHORIZED.name)
        ]
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            group.algorithm_project_id = 1
            group.algorithm_id = 2
            group.dataset_id = 2
            group.set_config(get_workflow_config(ModelJobType.TRAINING))
            algorithm_project_list = AlgorithmProjectList()
            algorithm_project_list.algorithm_projects['test'] = 'uuid-test'
            algorithm_project_list.algorithm_projects['demo1'] = 'uuid-demo1'
            algorithm_project_list.algorithm_projects['demo2'] = 'uuid-demo2'
            group.set_algorithm_project_uuid_list(algorithm_project_list)
            group.comment = 'comment'
            group.latest_version = 1
            model_job = ModelJob(name='job-1', group_id=1)
            session.add(model_job)
            session.commit()
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.maxDiff = None
        self.assertResponseDataEqual(resp, {
            'id': 1,
            'uuid': 'uuid',
            'name': 'group',
            'project_id': 1,
            'role': 'PARTICIPANT',
            'creator_username': 'ada',
            'coordinator_id': 0,
            'authorized': False,
            'auto_update_status': 'INITIAL',
            'dataset_id': 2,
            'algorithm_type': 'NN_VERTICAL',
            'algorithm_project_id': 1,
            'algorithm_id': 2,
            'comment': 'comment',
            'cron_config': '',
            'configured': True,
            'latest_version': 1,
            'config': to_dict(get_workflow_config(ModelJobType.TRAINING)),
            'latest_job_state': 'PENDING',
            'auth_frontend_status': 'SELF_AUTH_PENDING',
            'auth_status': 'PENDING',
            'created_at': 1651795200,
            'algorithm_project_uuid_list': {
                'algorithm_projects': {
                    'test': 'uuid-test',
                    'demo1': 'uuid-demo1',
                    'demo2': 'uuid-demo2'
                }
            },
            'participants_info': {
                'participants_map': {
                    'test': {
                        'auth_status': 'PENDING',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': ''
                    },
                    'demo1': {
                        'auth_status': 'AUTHORIZED',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': ''
                    },
                    'demo2': {
                        'auth_status': 'AUTHORIZED',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': ''
                    }
                }
            },
        },
                                     ignore_fields=['model_jobs', 'updated_at', 'start_data_batch_id'])
        data = self.get_response_data(resp)
        self.assertEqual(len(data['model_jobs']), 1)
        self.assertPartiallyEqual(data['model_jobs'][0], {
            'id': 1,
            'name': 'job-1',
            'role': 'PARTICIPANT',
            'model_job_type': 'UNSPECIFIED',
            'algorithm_type': 'UNSPECIFIED',
            'state': 'PENDING_ACCEPT',
            'group_id': 1,
            'status': 'PENDING',
            'uuid': '',
            'configured': False,
            'creator_username': '',
            'coordinator_id': 0,
            'version': 0,
            'project_id': 0,
            'started_at': 0,
            'stopped_at': 0,
            'metric_is_public': False,
            'algorithm_id': 0,
            'auth_status': 'PENDING',
            'auto_update': False,
            'auth_frontend_status': 'SELF_AUTH_PENDING',
            'participants_info': {
                'participants_map': {}
            }
        },
                                  ignore_fields=['created_at', 'updated_at'])

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_model_job_group')
    def test_put_model_job_group(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        config = get_workflow_config(ModelJobType.TRAINING)
        resp = self.put_helper('/api/v2/projects/1/model_job_groups/1',
                               data={
                                   'authorized': True,
                                   'algorithm_id': 1,
                                   'config': to_dict(config),
                                   'comment': 'comment'
                               })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            self.assertTrue(group.authorized)
            self.assertEqual(group.algorithm_id, 1)
            self.assertEqual(group.algorithm_project_id, 123)
            self.assertEqual(group.algorithm_type, AlgorithmType.NN_VERTICAL)
            self.assertEqual(group.get_config(), config)
            self.assertEqual(group.comment, 'comment')
            self.assertEqual(group.to_proto().configured, True)
            participants_info = group.get_participants_info()
            self.assertEqual(participants_info.participants_map['test'].auth_status, AuthStatus.AUTHORIZED.name)
            self.assertEqual(mock_client.call_args_list, [(('uuid', AuthStatus.AUTHORIZED),),
                                                          (('uuid', AuthStatus.AUTHORIZED),)])

    @patch('fedlearner_webconsole.mmgr.model_job_configer.ModelJobConfiger.get_config')
    def test_put_model_job_group_with_global_config(self, mock_get_config):
        mock_get_config.return_value = get_workflow_config(ModelJobType.EVALUATION)
        global_config = get_global_config()
        resp = self.put_helper('/api/v2/projects/1/model_job_groups/1',
                               data={
                                   'dataset_id': 1,
                                   'global_config': to_dict(global_config)
                               })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_get_config.assert_called_with(dataset_id=1,
                                           model_id=None,
                                           model_job_config=global_config.global_config['test'])
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).get(1)
            self.assertEqual(group.dataset_id, 1)
            self.assertEqual(group.get_config(), get_workflow_config(ModelJobType.EVALUATION))

    @patch('fedlearner_webconsole.mmgr.service.ModelJobGroupService.update_cronjob_config')
    def test_put_model_job_group_with_cron_config(self, mock_cronjob_config: Mock):
        resp = self.put_helper('/api/v2/projects/1/model_job_groups/1', data={})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_cronjob_config.assert_not_called()
        self.put_helper('/api/v2/projects/1/model_job_groups/1', data={
            'cron_config': '*/10 * * * *',
        })
        mock_cronjob_config.assert_called_once_with(group=ANY, cron_config='*/10 * * * *')
        self.put_helper('/api/v2/projects/1/model_job_groups/1', data={
            'cron_config': '',
        })
        mock_cronjob_config.assert_called_with(group=ANY, cron_config='')

    def test_delete_model_job_group(self):
        resp = self.delete_helper('/api/v2/projects/1/model_job_groups/1')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            group = session.query(ModelJobGroup).execution_options(include_deleted=True).get(1)
            self.assertIsNotNone(group.deleted_at)
            for job in group.model_jobs:
                self.assertIsNotNone(job.deleted_at)


class PeerModelJobGroupApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant = Participant(id=1, name='party', domain_name='fl-peer.com', host='127.0.0.1', port=32443)
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            group = ModelJobGroup(id=1, name='group', uuid='uuid', project_id=1, dataset_id=1)
            session.add_all([project, participant, relationship, group])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.system_service_client.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_model_job_group')
    def test_get_peer_model_job_group(self, mock_get_group, mock_list_flags):
        config = WorkflowDefinition(job_definitions=[JobDefinition(variables=[Variable(name='test')])])
        mock_get_group.return_value = ModelJobGroupPb(name='group', uuid='uuid', config=config)
        mock_list_flags.return_value = {'model_job_global_config_enabled': True}
        resp = self.get_helper('/api/v2/projects/1/model_job_groups/1/peers/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_get_group.assert_called()
        data = self.get_response_data(resp)
        self.assertEqual(data['name'], 'group')
        self.assertEqual(data['uuid'], 'uuid')

    @patch('fedlearner_webconsole.rpc.client.RpcClient.update_model_job_group')
    def test_patch_peer_model_job_group(self, mock_update_group):
        config = get_workflow_config(ModelJobType.TRAINING)
        mock_update_group.return_value = UpdateModelJobGroupResponse(uuid='uuid', config=config)
        resp = self.patch_helper('/api/v2/projects/1/model_job_groups/1/peers/1', data={'config': to_dict(config)})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_update_group.assert_called_with(model_job_group_uuid='uuid', config=config)

    @patch('fedlearner_webconsole.rpc.client.RpcClient.update_model_job_group')
    @patch('fedlearner_webconsole.mmgr.model_job_configer.ModelJobConfiger.get_config')
    def test_patch_peer_model_job_group_with_global_config(self, mock_get_config, mock_update_group):
        config = get_workflow_config(ModelJobType.TRAINING)
        mock_get_config.return_value = config
        mock_update_group.return_value = UpdateModelJobGroupResponse(uuid='uuid', config=config)
        global_config = get_global_config()
        resp = self.patch_helper('/api/v2/projects/1/model_job_groups/1/peers/1',
                                 data={'global_config': to_dict(global_config)})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_get_config.assert_called_with(dataset_id=1,
                                           model_id=None,
                                           model_job_config=global_config.global_config['peer'])
        mock_update_group.assert_called_with(model_job_group_uuid='uuid', config=config)


class StopAutoUpdateApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            participant = Participant(id=1, name='party', domain_name='fl-peer.com', host='127.0.0.1', port=32443)
            group = ModelJobGroup(id=1,
                                  name='group',
                                  uuid='uuid',
                                  project_id=1,
                                  dataset_id=1,
                                  auto_update_status=GroupAutoUpdateStatus.ACTIVE,
                                  start_data_batch_id=1)
            session.add_all([project, participant, relationship, group])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.update_model_job_group')
    def test_post_stop(self, mock_client: MagicMock):
        mock_client.return_value = Empty()
        resp = self.post_helper('/api/v2/projects/1/model_job_groups/1:stop_auto_update')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['auto_update_status'], GroupAutoUpdateStatus.STOPPED.name)
        self.assertEqual(
            mock_client.call_args_list,
            [call(uuid='uuid', auto_update_status=GroupAutoUpdateStatus.STOPPED, start_dataset_job_stage_uuid=None)])


if __name__ == '__main__':
    unittest.main()
