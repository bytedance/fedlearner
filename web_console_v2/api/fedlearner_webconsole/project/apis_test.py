# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import json
import unittest
from datetime import datetime, timezone

from http import HTTPStatus
from unittest.mock import patch, MagicMock

from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.participant.models import Participant, ProjectParticipant, ParticipantType
from fedlearner_webconsole.project.apis import _add_variable
from fedlearner_webconsole.project.controllers import ParticipantResp
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.pp_time import sleep
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project, PendingProject, PendingProjectState, ProjectRole
from fedlearner_webconsole.proto.project_pb2 import ProjectConfig, ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.workflow.models import Workflow
from testing.common import BaseTestCase


class ProjectApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.signin_as_admin()
        self.default_project = Project()
        self.default_project.name = 'test-default_project'
        self.default_project.set_config(ParseDict({'variables': [{'name': 'test', 'value': 'test'}]}, ProjectConfig()))
        self.default_project.comment = 'test comment'

        workflow = Workflow(name='workflow_key_get1', project_id=1)
        participant = Participant(name='test-participant', domain_name='fl-test.com', host='127.0.0.1', port=32443)
        relationship = ProjectParticipant(project_id=1, participant_id=1)
        with db.session_scope() as session:
            session.add(self.default_project)
            session.add(workflow)
            session.add(participant)
            session.add(relationship)
            session.commit()

    def test_add_variable(self):
        # test none
        self.assertEqual(_add_variable(None, 'storage_root_path', '/data'),
                         {'variables': [{
                             'name': 'storage_root_path',
                             'value': '/data'
                         }]})
        # test variables is []
        self.assertEqual(_add_variable({'variables': []}, 'storage_root_path', '/data'),
                         {'variables': [{
                             'name': 'storage_root_path',
                             'value': '/data'
                         }]})
        # test has other variables
        self.assertEqual(
            _add_variable({'variables': [{
                'name': 'test-post',
                'value': 'test'
            }]}, 'storage_root_path', '/data'),
            {'variables': [{
                'name': 'test-post',
                'value': 'test'
            }, {
                'name': 'storage_root_path',
                'value': '/data'
            }]})
        # test already set storage_root_path
        self.assertEqual(
            _add_variable({'variables': [{
                'name': 'storage_root_path',
                'value': '/fake_data'
            }]}, 'storage_root_path', '/data'), {'variables': [{
                'name': 'storage_root_path',
                'value': '/fake_data'
            }]})

    def test_get_project(self):
        get_response = self.get_helper('/api/v2/projects/1')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        queried_project = json.loads(get_response.data).get('data')
        with db.session_scope() as session:
            project_in_db = session.query(Project).get(1)
            self.assertEqual(queried_project, to_dict(project_in_db.to_proto()))

    def test_get_not_found_project(self):
        get_response = self.get_helper(f'/api/v2/projects/{1000}')
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_project_by_new_participant(self):
        name = 'test-post-project'
        comment = 'test post project(by new participant)'
        config = {'variables': [{'name': 'test-post', 'value': 'test'}]}
        create_response = self.post_helper('/api/v2/projects',
                                           data={
                                               'name': name,
                                               'comment': comment,
                                               'config': config,
                                               'participant_ids': [2]
                                           })

        self.assertEqual(create_response.status_code, HTTPStatus.CREATED)
        created_project = self.get_response_data(create_response)

        with db.session_scope() as session:
            relationship = session.query(ProjectParticipant).all()
            queried_project = session.query(Project).filter_by(name=name).first()

            self.assertEqual((relationship[1].project_id, relationship[1].participant_id), (2, 2))
            self.assertEqual(created_project, to_dict(queried_project.to_proto()))

    def test_post_conflict_name_project(self):
        create_response = self.post_helper('/api/v2/projects',
                                           data={
                                               'name': self.default_project.name,
                                               'participant_ids': [1],
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.CONFLICT)

    def test_list_project(self):
        list_response = self.get_helper('/api/v2/projects')
        project_list = self.get_response_data(list_response)
        self.assertEqual(len(project_list), 1)
        project_id = project_list[0]['id']
        with db.session_scope() as session:
            queried_project = session.query(Project).get(project_id)
            ref = queried_project.to_ref()
            ref.num_workflow = 1
            self.assertEqual(project_list[0], to_dict(ref))

    def test_update_project(self):
        updated_comment = 'updated comment'
        variables = [{'name': 'test-variables', 'value': 'variables'}]
        update_response = self.patch_helper('/api/v2/projects/1',
                                            data={
                                                'comment': updated_comment,
                                                'variables': variables,
                                            })
        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        # test response
        project = self.get_response_data(update_response)
        self.assertEqual(project['comment'], updated_comment)
        self.assertEqual(project['variables'], [{
            'access_mode': 'UNSPECIFIED',
            'name': 'test-variables',
            'value': 'variables',
            'value_type': 'STRING',
            'tag': '',
            'widget_schema': ''
        }])
        # test database
        get_response = self.get_helper('/api/v2/projects/1')
        project = self.get_response_data(get_response)
        self.assertEqual(project['comment'], updated_comment)

    def test_update_project_config(self):
        config = {'variables': [{'name': 'test-variables', 'value': 'variables'}]}
        update_response = self.patch_helper('/api/v2/projects/1', data={
            'config': config,
        })
        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        # test database
        get_response = self.get_helper('/api/v2/projects/1')
        project = self.get_response_data(get_response)
        config = {
            'abilities': [],
            'action_rules': {},
            'support_blockchain':
                False,
            'variables': [{
                'access_mode': 'UNSPECIFIED',
                'name': 'test-variables',
                'tag': '',
                'value': 'variables',
                'value_type': 'STRING',
                'widget_schema': ''
            }]
        }
        self.assertEqual(project['config'], config)

    def test_update_not_found_project(self):
        updated_comment = 'updated comment'
        update_response = self.patch_helper(f'/api/v2/projects/{1000}', data={'comment': updated_comment})
        self.assertEqual(update_response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_project_with_multiple_participants(self):
        create_response = self.post_helper('/api/v2/projects',
                                           data={
                                               'name': 'test name',
                                               'comment': 'test comment',
                                               'participant_ids': [1, 2, 3]
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.BAD_REQUEST)

    def test_post_project_with_light_client(self):
        with db.session_scope() as session:
            light_participant = Participant(name='light-client',
                                            type=ParticipantType.LIGHT_CLIENT,
                                            domain_name='fl-light-client.com',
                                            host='127.0.0.1',
                                            port=32443)
            session.add(light_participant)
            session.commit()
        resp = self.post_helper('/api/v2/projects',
                                data={
                                    'name': 'test-project',
                                    'comment': 'test comment',
                                    'participant_ids': [light_participant.id]
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name='test-project').first()
            self.assertEqual(project.participants[0].name, 'light-client')
            self.assertEqual(project.get_participant_type(), ParticipantType.LIGHT_CLIENT)


class ProjectParticipantsApi(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.participant_1 = Participant(name='participant pro1', domain_name='fl-participant-1.com')
        self.participant_2 = Participant(name='participant pro2', domain_name='fl-participant-2.com')
        self.project_1 = Project(name='project 1')
        self.relationship_11 = ProjectParticipant(project_id=1, participant_id=1)
        self.relationship_12 = ProjectParticipant(project_id=1, participant_id=2)
        with db.session_scope() as session:
            session.add(self.participant_1)
            session.flush()
            sleep(1)
            session.add(self.participant_2)
            session.add(self.project_1)
            session.add(self.relationship_11)
            session.add(self.relationship_12)
            session.commit()

    def test_get_project_participants(self):
        get_response = self.get_helper('/api/v2/projects/1/participants')
        participants = self.get_response_data(get_response)
        self.assertEqual(len(participants), 2)
        self.assertEqual(participants[0]['name'], 'participant pro2')
        self.assertEqual(participants[0]['pure_domain_name'], 'participant-2')
        self.assertEqual(participants[1]['name'], 'participant pro1')
        self.assertEqual(participants[1]['pure_domain_name'], 'participant-1')


class PendingProjectsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.participant_1 = Participant(name='participant pro1', domain_name='fl-participant-1.com')
        self.participant_2 = Participant(name='participant pro2', domain_name='fl-participant-2.com')
        with db.session_scope() as session:
            session.add(self.participant_1)
            session.add(self.participant_2)
            session.commit()

    def test_post_pending_projects(self):
        resp = self.post_helper('/api/v2/pending_projects',
                                data={
                                    'name': 'test-project',
                                    'comment': 'test comment',
                                    'config': {
                                        'variables': []
                                    },
                                    'participant_ids': [self.participant_1.id, self.participant_2.id]
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        resp = self.post_helper('/api/v2/pending_projects',
                                data={
                                    'name': 'test-project',
                                    'comment': 'test comment',
                                    'participant_ids': []
                                })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        with db.session_scope() as session:
            pending_project: PendingProject = session.query(PendingProject).filter_by(name='test-project').first()
            self.assertEqual(pending_project.role, ProjectRole.COORDINATOR)
            self.assertEqual(pending_project.state, PendingProjectState.ACCEPTED)
            self.assertEqual(pending_project.creator_username, 'ada')
            expected_info = ParticipantsInfo(
                participants_map={
                    'participant-1':
                        ParticipantInfo(name='participant pro1',
                                        role=ProjectRole.PARTICIPANT.name,
                                        state=PendingProjectState.PENDING.name,
                                        type=ParticipantType.PLATFORM.name),
                    'participant-2':
                        ParticipantInfo(name='participant pro2',
                                        role=ProjectRole.PARTICIPANT.name,
                                        state=PendingProjectState.PENDING.name,
                                        type=ParticipantType.PLATFORM.name),
                    '':
                        ParticipantInfo(role=ProjectRole.COORDINATOR.name,
                                        state=PendingProjectState.ACCEPTED.name,
                                        type=ParticipantType.PLATFORM.name)
                })
            self.assertEqual(pending_project.get_participants_info(), expected_info)

    @patch('fedlearner_webconsole.project.apis.PendingProjectService.list_pending_projects')
    def test_get_pending_projects(self, mock_list):
        created_at = datetime(2022, 5, 10, 0, 0, 0)
        updated_at = datetime(2022, 5, 10, 0, 0, 0)
        pending_proj = PendingProject(id=123,
                                      name='test',
                                      uuid='uuid',
                                      state=PendingProjectState.ACCEPTED,
                                      role=ProjectRole.PARTICIPANT,
                                      comment='test',
                                      created_at=created_at,
                                      updated_at=updated_at,
                                      ticket_status=TicketStatus.PENDING)
        mock_list.return_value.get_items.return_value = [pending_proj]
        mock_list.return_value.get_metadata.return_value = {
            'current_page': 1,
            'page_size': 1,
            'total_pages': 1,
            'total_items': 1
        }
        resp = self.get_helper('/api/v2/pending_projects')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(len(self.get_response_data(resp)), 1)


class PendingProjectApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.project.apis.PendingProjectService.update_state_as_participant')
    @patch('fedlearner_webconsole.project.apis.PendingProjectRpcController.sync_pending_project_state_to_coordinator')
    def test_patch_pending_project(self, mock_sync: MagicMock, mock_update: MagicMock):
        pending_project = PendingProject(name='test', state=PendingProjectState.PENDING, role=ProjectRole.PARTICIPANT)
        with db.session_scope() as session:
            session.add(pending_project)
            session.commit()
        mock_sync.return_value = ParticipantResp(succeeded=True, resp=None, msg='')
        mock_update.return_value = PendingProject(name='test',
                                                  state=PendingProjectState.PENDING,
                                                  role=ProjectRole.PARTICIPANT,
                                                  created_at=datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc),
                                                  updated_at=datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc),
                                                  ticket_status=TicketStatus.APPROVED)
        resp = self.patch_helper(f'/api/v2/pending_project/{pending_project.id}',
                                 data={
                                     'state': PendingProjectState.ACCEPTED.name,
                                 })
        mock_sync.assert_called_once_with(uuid=pending_project.uuid, state=PendingProjectState.ACCEPTED)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        mock_update.assert_called_once_with(pending_project.id, PendingProjectState.ACCEPTED.name)

    @patch('fedlearner_webconsole.project.apis.PendingProjectRpcController.send_to_participants')
    def test_delete_pending_project(self, mock_sync_delete: MagicMock):
        pending_project = PendingProject(name='test', state=PendingProjectState.PENDING, role=ProjectRole.PARTICIPANT)
        with db.session_scope() as session:
            session.add(pending_project)
            session.commit()
        mock_sync_delete.return_value = {
            'a': ParticipantResp(succeeded=True, resp=None, msg=''),
            'b': ParticipantResp(succeeded=False, resp=None, msg='aa')
        }
        resp = self.delete_helper(f'/api/v2/pending_project/{pending_project.id}')
        self.assertEqual(resp.status_code, 500)
        mock_sync_delete.assert_called_once()
        with db.session_scope() as session:
            self.assertIsNotNone(session.query(PendingProject).get(pending_project.id))
        mock_sync_delete.return_value = {
            'a': ParticipantResp(succeeded=True, resp=None, msg=''),
            'b': ParticipantResp(succeeded=True, resp=None, msg='aa')
        }
        self.delete_helper(f'/api/v2/pending_project/{pending_project.id}')

        self.assertEqual(mock_sync_delete.call_count, 2)
        with db.session_scope() as session:
            self.assertIsNone(session.query(PendingProject).get(pending_project.id))


if __name__ == '__main__':
    unittest.main()
