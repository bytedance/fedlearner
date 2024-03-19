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
from unittest.mock import patch, MagicMock
from datetime import datetime

import grpc
from google.protobuf.text_format import MessageToString
from google.protobuf.json_format import MessageToDict
from google.protobuf.empty_pb2 import Empty
from testing.common import BaseTestCase
from testing.rpc.client import FakeRpcError
from http import HTTPStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, AlgorithmType
from fedlearner_webconsole.dataset.models import Dataset, DataBatch
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobStatus, \
    GroupCreateStatus, TrustedJobType
from fedlearner_webconsole.proto.tee_pb2 import ParticipantDataset, ParticipantDatasetList, Resource
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.job.models import JobType, Job, JobState
from fedlearner_webconsole.proto.rpc.v2 import system_service_pb2
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import GetTrustedJobGroupResponse
from fedlearner_webconsole.setting.service import SettingService


class TrustedJobGroupsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        project = Project(id=1, name='project')
        participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
        participant2 = Participant(id=2, name='part3', domain_name='fl-domain3.com')
        proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
        proj_part2 = ProjectParticipant(project_id=1, participant_id=2)
        dataset1 = Dataset(id=1, name='dataset-name1', uuid='dataset-uuid1', is_published=True)
        dataset2 = Dataset(id=2, name='dataset-name2', uuid='dataset-uuid2', is_published=False)
        algorithm = Algorithm(id=1,
                              uuid='algorithm-uuid1',
                              algorithm_project_id=1,
                              type=AlgorithmType.TRUSTED_COMPUTING)
        algorithm_proj = AlgorithmProject(id=1, uuid='algorithm-proj-uuid')
        resource = MessageToString(Resource(cpu=1, memory=1, replicas=1))
        group1 = TrustedJobGroup(name='g1',
                                 project_id=1,
                                 coordinator_id=0,
                                 created_at=datetime(2021, 1, 1, 0, 0, 1),
                                 resource=resource)
        group2 = TrustedJobGroup(name='g2-filter',
                                 project_id=1,
                                 coordinator_id=0,
                                 created_at=datetime(2021, 1, 1, 0, 0, 2),
                                 resource=resource)
        group3 = TrustedJobGroup(name='g3',
                                 project_id=2,
                                 coordinator_id=0,
                                 created_at=datetime(2021, 1, 1, 0, 0, 3),
                                 resource=resource)
        group4 = TrustedJobGroup(name='g4-filter',
                                 project_id=1,
                                 coordinator_id=0,
                                 created_at=datetime(2021, 1, 1, 0, 0, 4),
                                 resource=resource)
        with db.session_scope() as session:
            session.add_all([
                project, participant1, participant2, proj_part1, proj_part2, dataset1, dataset2, algorithm,
                algorithm_proj
            ])
            session.add_all([group1, group2, group3, group4])
            session.commit()

    def test_get_trusted_groups(self):
        # get with project id 1
        resp = self.get_helper('/api/v2/projects/1/trusted_job_groups')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g4-filter', 'g2-filter', 'g1'])
        # get with project id 0
        resp = self.get_helper('/api/v2/projects/0/trusted_job_groups')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g4-filter', 'g3', 'g2-filter', 'g1'])
        # get with filter
        filter_param = urllib.parse.quote('(name~="filter")')
        resp = self.get_helper(f'/api/v2/projects/1/trusted_job_groups?filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g4-filter', 'g2-filter'])
        # get with page
        resp = self.get_helper(f'/api/v2/projects/1/trusted_job_groups?page=2&page_size=1&filter={filter_param}')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['g2-filter'])
        # get nothing for invalid project id
        resp = self.get_helper('/api/v2/projects/2/trusted_job_groups?page=2&page_size=1')
        self.assertEqual(self.get_response_data(resp), [])

    @patch('fedlearner_webconsole.rpc.v2.system_service_client.SystemServiceClient.check_tee_enabled')
    def test_post_trusted_job_groups(self, mock_client: MagicMock):
        mock_client.side_effect = [
            system_service_pb2.CheckTeeEnabledResponse(tee_enabled=True),
            system_service_pb2.CheckTeeEnabledResponse(tee_enabled=False),
        ]
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups',
                                data={
                                    'name': 'group-name',
                                    'comment': 'This is a comment.',
                                    'algorithm_uuid': 'algorithm-uuid1',
                                    'dataset_id': 1,
                                    'participant_datasets': [{
                                        'participant_id': 1,
                                        'uuid': 'dataset-uuid3',
                                        'name': 'dataset-name3',
                                    }],
                                    'resource': {
                                        'cpu': 2,
                                        'memory': 2,
                                        'replicas': 1,
                                    },
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).filter_by(name='group-name', project_id=1).first()
            self.assertEqual(group.name, 'group-name')
            self.assertEqual(group.latest_version, 0)
            self.assertEqual(group.comment, 'This is a comment.')
            self.assertEqual(group.project_id, 1)
            self.assertEqual(group.coordinator_id, 0)
            self.assertEqual(group.analyzer_id, 1)
            self.assertEqual(group.ticket_status, TicketStatus.APPROVED)
            self.assertEqual(group.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(group.unauth_participant_ids, '1,2')
            self.assertEqual(group.algorithm_uuid, 'algorithm-uuid1')
            self.assertEqual(group.resource, MessageToString(Resource(cpu=2, memory=2, replicas=1)))
            self.assertEqual(group.dataset_id, 1)
            participant_datasets = ParticipantDatasetList(
                items=[ParticipantDataset(
                    participant_id=1,
                    uuid='dataset-uuid3',
                    name='dataset-name3',
                )])
            self.assertEqual(group.participant_datasets, MessageToString(participant_datasets))

    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    @patch('fedlearner_webconsole.tee.apis.get_tee_enabled_participants')
    def test_post_trusted_job_groups_failed(self, mock_get_tee_enabled_participants: MagicMock,
                                            mock_get_algorithm: MagicMock):
        mock_get_algorithm.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'not found')
        mock_get_tee_enabled_participants.return_value = [0]
        resource = {'cpu': 2, 'memory': 2, 'replicas': 1}
        # fail due to no dataset is provided
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups',
                                data={
                                    'name': 'group-name',
                                    'algorithm_uuid': 'algorithm-uuid1',
                                    'resource': resource,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to dataset not found
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups',
                                data={
                                    'name': 'group-name',
                                    'algorithm_uuid': 'algorithm-uuid1',
                                    'dataset_id': 20,
                                    'resource': resource,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to dataset not published
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups',
                                data={
                                    'name': 'group-name',
                                    'algorithm_uuid': 'algorithm-uuid1',
                                    'dataset_id': 2,
                                    'resource': resource,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to participant not found
        resp = self.post_helper(
            '/api/v2/projects/1/trusted_job_groups',
            data={
                'name': 'group-name',
                'algorithm_uuid': 'algorithm-uuid1',
                'resource': resource,
                'participant_datasets': [{
                    'participant_id': 10,
                    'uuid': 'dataset-uuid3',
                    'name': 'dataset-name3',
                }],
            })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to algorithm not found
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups',
                                data={
                                    'name': 'group-name',
                                    'algorithm_uuid': 'algorithm-uuid10',
                                    'resource': resource,
                                    'dataset_id': 2,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # fail due to duplicate name in project
        with db.session_scope() as session:
            group = TrustedJobGroup(name='group-name', project_id=1)
            session.add(group)
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups',
                                data={
                                    'name': 'group-name',
                                    'algorithm_uuid': 'algorithm-uuid1',
                                    'resource': resource,
                                    'dataset_id': 1,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)


class TrustedJobGroupApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            algorithm_proj1 = AlgorithmProject(id=1, uuid='algo-proj-uuid1')
            algorithm1 = Algorithm(id=1, uuid='algorithm-uuid1', algorithm_project_id=1)
            participant = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            proj_part = ProjectParticipant(project_id=1, participant_id=1)
            group1 = TrustedJobGroup(id=1,
                                     name='group-name',
                                     uuid='uuid',
                                     comment='this is a comment',
                                     project_id=1,
                                     creator_username='admin',
                                     coordinator_id=0,
                                     created_at=datetime(2022, 7, 1, 0, 0, 0),
                                     updated_at=datetime(2022, 7, 1, 0, 0, 0),
                                     ticket_status=TicketStatus.APPROVED,
                                     status=GroupCreateStatus.SUCCEEDED,
                                     auth_status=AuthStatus.AUTHORIZED,
                                     unauth_participant_ids='1,2',
                                     algorithm_uuid='algorithm-uuid1')
            group1.set_resource(Resource(cpu=2, memory=2, replicas=1))
            group1.set_participant_datasets(
                ParticipantDatasetList(
                    items=[ParticipantDataset(participant_id=1, name='dataset-name', uuid='dataset-uuid')]))
            group2 = TrustedJobGroup(id=2,
                                     name='group-name2',
                                     uuid='uuid2',
                                     project_id=1,
                                     coordinator_id=1,
                                     ticket_status=TicketStatus.APPROVED,
                                     status=GroupCreateStatus.SUCCEEDED,
                                     auth_status=AuthStatus.AUTHORIZED,
                                     algorithm_uuid='algorithm-uuid1')
            session.add_all([project, group1, group2, algorithm_proj1, algorithm1, participant, proj_part])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_trusted_job_group')
    def test_get_trusted_job_group(self, mock_client: MagicMock):
        mock_client.return_value = GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        resp = self.get_helper('/api/v2/projects/1/trusted_job_groups/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        data.pop('updated_at')
        self.assertEqual(
            data, {
                'id': 1,
                'name': 'group-name',
                'comment': 'this is a comment',
                'analyzer_id': 0,
                'coordinator_id': 0,
                'created_at': 1656633600,
                'creator_username': 'admin',
                'dataset_id': 0,
                'latest_job_status': 'NEW',
                'latest_version': 0,
                'project_id': 1,
                'resource': {
                    'cpu': 2,
                    'memory': 2,
                    'replicas': 1
                },
                'status': 'SUCCEEDED',
                'algorithm_id': 1,
                'algorithm_uuid': 'algorithm-uuid1',
                'algorithm_project_uuid': 'algo-proj-uuid1',
                'algorithm_participant_id': 0,
                'auth_status': 'AUTHORIZED',
                'ticket_auth_status': 'AUTH_PENDING',
                'ticket_status': 'APPROVED',
                'ticket_uuid': '',
                'unauth_participant_ids': [2],
                'uuid': 'uuid',
                'participant_datasets': {
                    'items': [{
                        'participant_id': 1,
                        'name': 'dataset-name',
                        'uuid': 'dataset-uuid'
                    }]
                },
            })
        # failed due to not found
        resp = self.get_helper('/api/v2/projects/1/trusted_job_groups/10')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        # get nothing due to project invalid
        resp = self.get_helper('/api/v2/projects/10/trusted_job_groups/1')
        self.assertIsNone(self.get_response_data(resp))

    @patch('fedlearner_webconsole.algorithm.fetcher.AlgorithmFetcher.get_algorithm_from_participant')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.update_trusted_job_group')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_trusted_job_group')
    def test_put_trusted_job_group(self, mock_inform: MagicMock, mock_update: MagicMock, mock_get_algorithm: MagicMock):
        mock_get_algorithm.side_effect = FakeRpcError(grpc.StatusCode.NOT_FOUND, 'not found')
        mock_inform.return_value = None
        mock_update.return_value = None
        with db.session_scope() as session:
            algorithm_proj2 = AlgorithmProject(id=2, uuid='algo-proj-uuid2')
            algorithm2 = Algorithm(id=2, uuid='algorithm-uuid2', algorithm_project_id=1)
            algorithm3 = Algorithm(id=3, uuid='algorithm-uuid3', algorithm_project_id=2)
            session.add_all([algorithm_proj2, algorithm2, algorithm3])
            session.commit()
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/1',
                               data={
                                   'comment': 'new comment',
                                   'auth_status': 'PENDING',
                                   'algorithm_uuid': 'algorithm-uuid2',
                                   'resource': {
                                       'cpu': 4,
                                       'memory': 4,
                                       'replicas': 1
                                   }
                               })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).get(1)
            self.assertEqual(group.comment, 'new comment')
            self.assertEqual(group.auth_status, AuthStatus.PENDING)
            self.assertEqual(group.algorithm_uuid, 'algorithm-uuid2')
            self.assertEqual(group.resource, MessageToString(Resource(cpu=4, memory=4, replicas=1)))
        # failed due to group not found
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/10', data={'comment': 'new comment'})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        # failed due to not creator but update algorithm
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/2', data={'algorithm_uuid': 'algorithm-uuid2'})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        # failed due to algorithm not found
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/1',
                               data={'algorithm_uuid': 'algorithm-not-exist'})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # failed due to algorithm project mismatch
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/1', data={'algorithm_uuid': 'algorithm-uuid3'})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        # failed due to group not fully created
        with db.session_scope() as session:
            group3 = TrustedJobGroup(id=3, project_id=1, status=GroupCreateStatus.PENDING)
            session.add(group3)
            session.commit()
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/3', data={'comment': 'new comment'})
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)
        # failed due to grpc error, inconsistency in participants
        mock_update.side_effect = FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, 'mismatched algorithm project')
        resp = self.put_helper('/api/v2/projects/1/trusted_job_groups/1', data={'algorithm_uuid': 'algorithm-uuid1'})
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.delete_trusted_job_group')
    def test_delete_trusted_job_group(self, mock_delete: MagicMock):
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        mock_delete.return_value = None
        # fail due to trusted job is running
        with db.session_scope() as session:
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
            session.add_all([trusted_job1, job1, trusted_job2, job2])
            session.commit()
        resp = self.delete_helper('/api/v2/projects/1/trusted_job_groups/1')
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)
        # fail due to grpc err
        with db.session_scope() as session:
            session.query(TrustedJob).filter_by(id=1).update({'status': TrustedJobStatus.FAILED})
            session.commit()
        mock_delete.side_effect = FakeRpcError(grpc.StatusCode.FAILED_PRECONDITION, 'trusted job is not deletable')
        resp = self.delete_helper('/api/v2/projects/1/trusted_job_groups/1')
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        # fail due to not creator
        resp = self.delete_helper('/api/v2/projects/1/trusted_job_groups/2')
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        # successfully delete group not exist
        resp = self.delete_helper('/api/v2/projects/1/trusted_job_groups/3')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        # successfully delete
        mock_delete.side_effect = None
        resp = self.delete_helper('/api/v2/projects/1/trusted_job_groups/1')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            self.assertIsNone(session.query(TrustedJobGroup).get(1))
            self.assertIsNone(session.query(TrustedJob).get(1))
            self.assertIsNone(session.query(TrustedJob).get(2))
            self.assertIsNone(session.query(Job).get(1))
            self.assertIsNone(session.query(Job).get(2))


class LaunchTrustedJobApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            project = Project(id=1, name='project-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            algorithm = Algorithm(id=1,
                                  uuid='algorithm-uuid1',
                                  path='file:///data/algorithm/test',
                                  type=AlgorithmType.TRUSTED_COMPUTING)
            dataset1 = Dataset(id=1, name='dataset-name1', uuid='dataset-uuid1', is_published=True)
            data_batch1 = DataBatch(id=1, dataset_id=1)
            group = TrustedJobGroup(id=1,
                                    uuid='group-uuid',
                                    project_id=1,
                                    latest_version=1,
                                    coordinator_id=0,
                                    status=GroupCreateStatus.SUCCEEDED,
                                    auth_status=AuthStatus.AUTHORIZED,
                                    algorithm_uuid='algorithm-uuid1',
                                    dataset_id=1,
                                    resource=MessageToString(Resource(cpu=2000, memory=2, replicas=1)))
            session.add_all([project, participant1, proj_part1, algorithm, dataset1, data_batch1, group])
            sys_var = SettingService(session).get_system_variables_dict()
            session.commit()
        sys_var['sgx_image'] = 'artifact.bytedance.com/fedlearner/pp_bioinformatics:e13eb8a1d96ad046ca7354b8197d41fd'
        self.sys_var = sys_var

    @patch('fedlearner_webconsole.tee.services.get_batch_data_path')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_variables_dict')
    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_launch_trusted_job(self, mock_remote_do_two_pc: MagicMock, mock_get_system_info: MagicMock,
                                mock_get_system_variables_dict: MagicMock, mock_get_batch_data_path: MagicMock):
        mock_remote_do_two_pc.return_value = True, ''
        mock_get_system_info.return_value = SystemInfo(domain_name='domain1')
        mock_get_system_variables_dict.return_value = self.sys_var
        mock_get_batch_data_path.return_value = 'file:///data/test'
        # successful
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups/1:launch', data={'comment': 'this is a comment'})
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            trusted_job = session.query(TrustedJob).filter_by(trusted_job_group_id=1, version=2).first()
            self.assertIsNotNone(trusted_job)
            self.assertEqual(trusted_job.comment, 'this is a comment')
            self.assertEqual(trusted_job.coordinator_id, 0)
        # fail due to not found group
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups/10:launch', data={})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        # fail due to not fully auth
        with db.session_scope() as session:
            session.query(TrustedJobGroup).filter_by(id=1).update({'coordinator_id': 0, 'unauth_participant_ids': '1'})
            session.commit()
        resp = self.post_helper('/api/v2/projects/1/trusted_job_groups/1:launch', data={})
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)


class TrustedJobsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            trusted_job1 = TrustedJob(id=1,
                                      name='V1',
                                      version=1,
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      job_id=1,
                                      status=TrustedJobStatus.RUNNING)
            trusted_job2 = TrustedJob(id=2,
                                      name='V2',
                                      version=2,
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      job_id=2,
                                      status=TrustedJobStatus.SUCCEEDED)
            trusted_job3 = TrustedJob(id=3,
                                      name='V1',
                                      version=1,
                                      project_id=1,
                                      trusted_job_group_id=2,
                                      job_id=3,
                                      status=TrustedJobStatus.RUNNING)
            trusted_job4 = TrustedJob(id=4,
                                      name='V1',
                                      version=1,
                                      project_id=2,
                                      trusted_job_group_id=3,
                                      job_id=4,
                                      status=TrustedJobStatus.RUNNING)
            trusted_job5 = TrustedJob(id=5,
                                      name='V1-1',
                                      type=TrustedJobType.EXPORT,
                                      auth_status=AuthStatus.AUTHORIZED,
                                      version=1,
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      job_id=5,
                                      status=TrustedJobStatus.NEW,
                                      created_at=datetime(2022, 11, 23, 12, 0, 0))
            trusted_job6 = TrustedJob(id=6,
                                      name='V2-1',
                                      type=TrustedJobType.EXPORT,
                                      auth_status=AuthStatus.WITHDRAW,
                                      version=2,
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      job_id=6,
                                      status=TrustedJobStatus.CREATED,
                                      created_at=datetime(2022, 11, 23, 12, 0, 1))
            job1 = Job(id=1,
                       name='job-name1',
                       job_type=JobType.CUSTOMIZED,
                       workflow_id=0,
                       project_id=1,
                       state=JobState.FAILED)
            session.add_all([trusted_job1, trusted_job2, trusted_job3, trusted_job4, trusted_job5, trusted_job6, job1])
            session.commit()

    def test_get_trusted_job(self):
        # successful and trusted job status is refreshed when api is called
        resp = self.get_helper('/api/v2/projects/1/trusted_jobs?trusted_job_group_id=1')
        data = self.get_response_data(resp)
        self.assertEqual([(d['name'], d['status']) for d in data], [('V2', 'SUCCEEDED'), ('V1', 'FAILED')])

    def test_get_export_trusted_job(self):
        resp = self.get_helper('/api/v2/projects/1/trusted_jobs?trusted_job_group_id=1&type=EXPORT')
        data = self.get_response_data(resp)
        self.assertEqual([(d['name'], d['status']) for d in data], [('V2-1', 'CREATED'), ('V1-1', 'NEW')])


class TrustedJobApi(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            project = Project(id=1, name='project')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            self.participants_info = ParticipantsInfo(participants_map={
                'domain1': ParticipantInfo(auth_status='AUTHORIZED'),
                'domain2': ParticipantInfo(auth_status='PENDING'),
            })
            trusted_job1 = TrustedJob(id=1,
                                      name='V1',
                                      type=TrustedJobType.EXPORT,
                                      job_id=1,
                                      uuid='uuid1',
                                      version=1,
                                      comment='this is a comment',
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      status=TrustedJobStatus.PENDING,
                                      auth_status=AuthStatus.AUTHORIZED,
                                      algorithm_uuid='algorithm-uuid1',
                                      created_at=datetime(2022, 6, 14, 0, 0, 0),
                                      updated_at=datetime(2022, 6, 14, 0, 0, 1),
                                      participants_info=MessageToString(self.participants_info))
            job1 = Job(id=1,
                       name='job-name1',
                       job_type=JobType.CUSTOMIZED,
                       workflow_id=0,
                       project_id=1,
                       state=JobState.STARTED)
            session.add_all([project, participant1, proj_part1, trusted_job1, job1])
            session.commit()

    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.get_trusted_job')
    def test_get_trusted_job(self, mock_client: MagicMock):
        mock_client.return_value = GetTrustedJobGroupResponse(auth_status='AUTHORIZED')
        # successful
        resp = self.get_helper('/api/v2/projects/1/trusted_jobs/1')
        data = self.get_response_data(resp)
        part_info_dict = MessageToDict(
            self.participants_info,
            preserving_proto_field_name=True,
            including_default_value_fields=True,
        )
        part_info_dict['participants_map']['domain2']['auth_status'] = 'AUTHORIZED'
        del data['updated_at']
        self.assertEqual(
            data, {
                'algorithm_id': 0,
                'algorithm_uuid': 'algorithm-uuid1',
                'comment': 'this is a comment',
                'auth_status': 'AUTHORIZED',
                'export_dataset_id': 0,
                'finished_at': 0,
                'id': 1,
                'job_id': 1,
                'name': 'V1',
                'project_id': 1,
                'started_at': 0,
                'status': 'RUNNING',
                'ticket_status': 'APPROVED',
                'ticket_uuid': '',
                'trusted_job_group_id': 1,
                'coordinator_id': 0,
                'type': 'EXPORT',
                'uuid': 'uuid1',
                'version': 1,
                'created_at': 1655164800,
                'participants_info': part_info_dict,
                'ticket_auth_status': 'AUTHORIZED',
            })
        # fail due to not found
        resp = self.get_helper('/api/v2/projects/1/trusted_jobs/10')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    @patch('fedlearner_webconsole.rpc.v2.job_service_client.JobServiceClient.inform_trusted_job')
    def test_put_trusted_job(self, mock_client: MagicMock, mock_get_system_info: MagicMock):
        mock_client.return_value = Empty()
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        # successful update comment
        resp = self.put_helper('/api/v2/projects/1/trusted_jobs/1', data={'comment': 'new comment'})
        data = self.get_response_data(resp)
        self.assertEqual(data['comment'], 'new comment')
        # successful update auth_status
        resp = self.put_helper('/api/v2/projects/1/trusted_jobs/1', data={'auth_status': 'WITHDRAW'})
        data = self.get_response_data(resp)
        self.assertEqual(data['auth_status'], 'WITHDRAW')
        self.assertEqual(data['participants_info']['participants_map']['domain1']['auth_status'], 'WITHDRAW')
        # fail due to not found
        resp = self.put_helper('/api/v2/projects/1/trusted_jobs/10', data={'comment': 'new comment'})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)


class StopTrustedJobApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            project = Project(id=1, name='project-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            group = TrustedJobGroup(id=1,
                                    uuid='group-uuid',
                                    project_id=1,
                                    latest_version=1,
                                    coordinator_id=0,
                                    status=GroupCreateStatus.SUCCEEDED,
                                    auth_status=AuthStatus.AUTHORIZED,
                                    algorithm_uuid='algorithm-uuid')
            trusted_job1 = TrustedJob(id=1,
                                      uuid='trusted-job-uuid1',
                                      name='V1',
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      job_id=1,
                                      status=TrustedJobStatus.PENDING)
            job1 = Job(id=1,
                       name='job-name1',
                       job_type=JobType.CUSTOMIZED,
                       project_id=1,
                       workflow_id=0,
                       state=JobState.STARTED)
            session.add_all([project, participant1, proj_part1, group, trusted_job1, job1])
            session.commit()

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager._remote_do_two_pc')
    def test_stop_trusted_job(self, mock_remote_do_two_pc):
        mock_remote_do_two_pc.return_value = True, ''
        # successful and trusted job status is refreshed to RUNNING before STOPPED
        resp = self.post_helper('/api/v2/projects/1/trusted_jobs/1:stop')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            trusted_job1: TrustedJob = session.query(TrustedJob).get(1)
            self.assertEqual(trusted_job1.status, TrustedJobStatus.STOPPED)
        # fail due to not in RUNNING status since it is STOPPED before
        resp = self.post_helper('/api/v2/projects/1/trusted_jobs/1:stop')
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)
        # fail due to trusted job not found
        resp = self.post_helper('/api/v2/projects/10/trusted_jobs/1:stop')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)


class TrustedNotificationsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        resource = MessageToString(Resource(cpu=1, memory=2, replicas=1))
        with db.session_scope() as session:
            group1 = TrustedJobGroup(id=1, project_id=1, name='group1', resource=resource)
            group2 = TrustedJobGroup(id=2, project_id=1, name='group2', created_at=datetime(2022, 10, 1, 0, 0, 0))
            group3 = TrustedJobGroup(id=3, project_id=1, name='group3', resource=resource)
            group4 = TrustedJobGroup(id=4, project_id=2, name='group4', created_at=datetime(2022, 10, 1, 0, 0, 1))
            group5 = TrustedJobGroup(id=5, project_id=1, name='group5', created_at=datetime(2022, 10, 1, 0, 0, 4))
            trusted_job1 = TrustedJob(id=1,
                                      name='V10-1',
                                      auth_status=AuthStatus.PENDING,
                                      type=TrustedJobType.EXPORT,
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      created_at=datetime(2022, 10, 1, 0, 0, 2))
            trusted_job2 = TrustedJob(id=2,
                                      name='V10-2',
                                      auth_status=AuthStatus.WITHDRAW,
                                      type=TrustedJobType.EXPORT,
                                      project_id=1,
                                      trusted_job_group_id=1)
            trusted_job3 = TrustedJob(id=3,
                                      name='V10',
                                      auth_status=AuthStatus.PENDING,
                                      type=TrustedJobType.ANALYZE,
                                      project_id=1,
                                      trusted_job_group_id=1)
            trusted_job4 = TrustedJob(id=4,
                                      name='V9-1',
                                      auth_status=AuthStatus.PENDING,
                                      type=TrustedJobType.EXPORT,
                                      project_id=1,
                                      trusted_job_group_id=1,
                                      created_at=datetime(2022, 10, 1, 0, 0, 3))
            trusted_job5 = TrustedJob(id=5,
                                      name='V9-2',
                                      auth_status=AuthStatus.PENDING,
                                      type=TrustedJobType.EXPORT,
                                      project_id=2,
                                      trusted_job_group_id=4,
                                      created_at=datetime(2022, 10, 1, 0, 0, 5))

            session.add_all([
                group1, group2, group3, group4, group5, trusted_job1, trusted_job2, trusted_job3, trusted_job4,
                trusted_job5
            ])
            session.commit()

    def test_get_trusted_notifications(self):
        resp = self.get_helper('/api/v2/projects/1/trusted_notifications')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['group5', 'group1-V9-1', 'group1-V10-1', 'group2'])
        resp = self.get_helper('/api/v2/projects/2/trusted_notifications')
        data = self.get_response_data(resp)
        self.assertEqual([d['name'] for d in data], ['group4-V9-2', 'group4'])


class ExportTrustedJobApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        Flag.TRUSTED_COMPUTING_ENABLED.value = True
        with db.session_scope() as session:
            project = Project(id=1, name='project-name')
            participant1 = Participant(id=1, name='part2', domain_name='fl-domain2.com')
            proj_part1 = ProjectParticipant(project_id=1, participant_id=1)
            trusted_job1 = TrustedJob(id=1,
                                      uuid='uuid1',
                                      project_id=1,
                                      status=TrustedJobStatus.SUCCEEDED,
                                      version=1,
                                      trusted_job_group_id=1,
                                      resource=MessageToString(Resource(cpu=1, memory=1, replicas=1)))
            trusted_job2 = TrustedJob(id=2,
                                      uuid='uuid2',
                                      project_id=1,
                                      status=TrustedJobStatus.RUNNING,
                                      version=2,
                                      trusted_job_group_id=1)
            session.add_all([project, participant1, proj_part1, trusted_job1, trusted_job2])
            session.commit()

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info')
    def test_export_trusted_job(self, mock_get_system_info: MagicMock):
        mock_get_system_info.return_value = SystemInfo(pure_domain_name='domain1')
        # successful
        resp = self.post_helper('/api/v2/projects/1/trusted_jobs/1:export')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        resp = self.post_helper('/api/v2/projects/1/trusted_jobs/1:export')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            tee_export_job = session.query(TrustedJob).filter_by(type=TrustedJobType.EXPORT,
                                                                 version=1,
                                                                 project_id=1,
                                                                 trusted_job_group_id=1,
                                                                 export_count=1).first()
            self.assertEqual(tee_export_job.name, 'V1-domain1-1')
            self.assertEqual(tee_export_job.coordinator_id, 0)
            self.assertEqual(tee_export_job.status, TrustedJobStatus.NEW)
            self.assertIsNotNone(tee_export_job.ticket_uuid)
            tee_export_job = session.query(TrustedJob).filter_by(type=TrustedJobType.EXPORT,
                                                                 version=1,
                                                                 project_id=1,
                                                                 trusted_job_group_id=1,
                                                                 export_count=2).first()
            self.assertEqual(tee_export_job.name, 'V1-domain1-2')
            tee_analyze_job = session.query(TrustedJob).get(1)
            self.assertEqual(tee_analyze_job.export_count, 2)
        # not found
        resp = self.post_helper('/api/v2/projects/1/trusted_jobs/10:export')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        # not succeeded
        resp = self.post_helper('/api/v2/projects/1/trusted_jobs/2:export')
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)


if __name__ == '__main__':
    unittest.main()
