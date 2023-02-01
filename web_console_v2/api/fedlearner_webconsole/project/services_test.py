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
import time
import unittest
from unittest.mock import patch

from google.protobuf.struct_pb2 import Value

from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import ResourceConflictException
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant, ParticipantType
from fedlearner_webconsole.project.models import Project, ProjectRole, PendingProjectState, PendingProject
from fedlearner_webconsole.project.services import ProjectService, PendingProjectService
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterExpressionKind, SimpleExpression, FilterOp
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo, ProjectConfig
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.workflow.models import Workflow
from testing.no_web_server_test_case import NoWebServerTestCase


class ProjectServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project_1 = Project(id=1, name='project 1', creator='user1')
            participant_1 = Participant(id=1, name='participant 1', domain_name='fl-participant-1.com')
            relation = ProjectParticipant(project_id=project_1.id, participant_id=participant_1.id)
            session.add_all([project_1, participant_1, relation])
            session.commit()
            time.sleep(1)

            project_2 = Project(id=2, name='project 2', creator='user2')
            participant_2 = Participant(id=2, name='participant 2', domain_name='fl-participant-2.com')
            relation_1 = ProjectParticipant(project_id=project_1.id, participant_id=participant_2.id)
            relation_2 = ProjectParticipant(project_id=project_2.id, participant_id=participant_2.id)
            session.add_all([project_2, participant_2, relation_1, relation_2])

            session.commit()

    def test_get_projects_by_participant_id(self):
        with db.session_scope() as session:
            service = ProjectService(session)
            projects = service.get_projects_by_participant(1)
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].name, 'project 1')

            projects = service.get_projects_by_participant(2)
            self.assertEqual(len(projects), 2)
            self.assertCountEqual([projects[0].name, projects[1].name], ['project 1', 'project 2'])

    def test_get_projects(self):
        with db.session_scope() as session:
            workflow_1 = Workflow(name='workflow 1', project_id=1)
            workflow_2 = Workflow(name='workflow 2', project_id=1)
            session.add_all([workflow_1, workflow_2])
            session.commit()
        with db.session_scope() as session:
            service = ProjectService(session)
            projects = service.get_projects()
            self.assertEqual(len(projects), 2)

            self.assertEqual(projects[0].name, 'project 2')
            self.assertEqual(len(projects[0].participants), 1)
            self.assertEqual(projects[0].num_workflow, 0)

            self.assertEqual(projects[1].name, 'project 1')
            self.assertEqual(len(projects[1].participants), 2)
            self.assertEqual(projects[1].num_workflow, 2)


class PendingProjectServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            participant_1 = Participant(id=1,
                                        name='participant 1',
                                        domain_name='fl-participant-1.com',
                                        type=ParticipantType.LIGHT_CLIENT)
            participant_2 = Participant(id=2,
                                        name='participant 2',
                                        domain_name='fl-participant-2.com',
                                        type=ParticipantType.PLATFORM)
            session.add_all([participant_1, participant_2])
            session.commit()

    @patch('fedlearner_webconsole.project.services.SettingService.get_system_info')
    def test_build_participants_info(self, mock_system_info):
        mock_system_info.return_value = SystemInfo(pure_domain_name='self', name='self_name')
        with db.session_scope() as session:
            info = PendingProjectService(session).build_participants_info([1, 2])
            self.assertEqual(
                info,
                ParticipantsInfo(
                    participants_map={
                        'participant-1':
                            ParticipantInfo(name='participant 1',
                                            role=ProjectRole.PARTICIPANT.name,
                                            state=PendingProjectState.ACCEPTED.name,
                                            type=ParticipantType.LIGHT_CLIENT.name),
                        'participant-2':
                            ParticipantInfo(name='participant 2',
                                            role=ProjectRole.PARTICIPANT.name,
                                            state=PendingProjectState.PENDING.name,
                                            type=ParticipantType.PLATFORM.name),
                        'self':
                            ParticipantInfo(name='self_name',
                                            role=ProjectRole.COORDINATOR.name,
                                            state=PendingProjectState.ACCEPTED.name,
                                            type=ParticipantType.PLATFORM.name)
                    }))

    def test_get_ids_from_participants_info(self):
        participants_info = ParticipantsInfo(
            participants_map={
                'participant-1': ParticipantInfo(name='participant 1'),
                'participant-2': ParticipantInfo(name='participant 2'),
                'self': ParticipantInfo(name='self', role=ProjectRole.COORDINATOR.name),
                'no connection': ParticipantInfo(name='no connection')
            })
        with db.session_scope() as session:
            ids = PendingProjectService(session).get_ids_from_participants_info(participants_info)
            self.assertCountEqual(ids, [1, 2])

    def test_create_pending_project(self):
        with db.session_scope() as session:
            pending_project = PendingProjectService(session).create_pending_project(
                name='test',
                config=ProjectConfig(variables=[Variable(name='test')]),
                participants_info=ParticipantsInfo(
                    participants_map={'self': ParticipantInfo(name='self', role=ProjectRole.COORDINATOR.name)}),
                comment='test',
                creator_username='test',
                uuid='uuid')
            session.commit()
        with db.session_scope() as session:
            result: PendingProject = session.query(PendingProject).get(pending_project.id)
        self.assertEqual(result.get_config(), ProjectConfig(variables=[Variable(name='test')]))
        self.assertEqual(
            result.get_participants_info(),
            ParticipantsInfo(
                participants_map={'self': ParticipantInfo(name='self', role=ProjectRole.COORDINATOR.name)}))
        self.assertEqual(result.name, 'test')
        self.assertEqual(result.uuid, 'uuid')

    @patch('fedlearner_webconsole.project.services.PendingProjectService.duplicated_name_exists')
    def test_update_state_as_participant(self, mock_dup):
        pending_project = PendingProject(name='test', state=PendingProjectState.PENDING, role=ProjectRole.PARTICIPANT)

        with db.session_scope() as session:
            session.add(pending_project)
            session.commit()

        mock_dup.return_value = True
        with db.session_scope() as session:
            with self.assertRaises(ResourceConflictException):
                PendingProjectService(session).update_state_as_participant(pending_project.id,
                                                                           PendingProjectState.ACCEPTED.name)
        with db.session_scope() as session:
            PendingProjectService(session).update_state_as_participant(pending_project.id,
                                                                       PendingProjectState.CLOSED.name)
            session.commit()
        with db.session_scope() as session:
            result: PendingProject = session.query(PendingProject).get(pending_project.id)
            self.assertEqual(result.state, PendingProjectState.CLOSED)

    def test_create_project_locally(self):
        with db.session_scope() as session:
            pending_project = PendingProjectService(session).create_pending_project(
                name='test',
                config=ProjectConfig(variables=[Variable(name='test')]),
                participants_info=ParticipantsInfo(
                    participants_map={'self': ParticipantInfo(name='self', role=ProjectRole.COORDINATOR.name)}),
                comment='test',
                creator_username='test',
                uuid='uuid')
            session.commit()

        with db.session_scope() as session:
            PendingProjectService(session).create_project_locally(pending_project.uuid)
            session.commit()
        with db.session_scope() as session:
            project = session.query(Project).filter_by(name=pending_project.name, token=pending_project.uuid).first()
            self.assertEqual(project.get_variables(), [
                Variable(name='test'),
                Variable(name='storage_root_path',
                         value=Envs.STORAGE_ROOT,
                         typed_value=Value(string_value=Envs.STORAGE_ROOT))
            ])
            pending_project = session.query(PendingProject).get(pending_project.id)
            self.assertEqual(
                project.get_participants_info(),
                ParticipantsInfo(
                    participants_map={'self': ParticipantInfo(name='self', role=ProjectRole.COORDINATOR.name)}))
            self.assertEqual(project.creator, 'test')
            self.assertEqual(pending_project.state, PendingProjectState.CLOSED)
            self.assertEqual(project.comment, 'test')

    def test_list_pending_projects(self):
        pending_project = PendingProject(name='test', state=PendingProjectState.PENDING, role=ProjectRole.PARTICIPANT)
        pending_project1 = PendingProject(name='test1',
                                          state=PendingProjectState.ACCEPTED,
                                          role=ProjectRole.COORDINATOR)
        with db.session_scope() as session:
            session.add(pending_project)
            session.add(pending_project1)
            session.commit()
        with db.session_scope() as session:
            result = PendingProjectService(session).list_pending_projects().get_items()
            self.assertEqual(len(result), 2)
            result = PendingProjectService(session).list_pending_projects(page=1, page_size=1).get_items()
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].id, pending_project1.id)
            exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                   simple_exp=SimpleExpression(field='role',
                                                               op=FilterOp.EQUAL,
                                                               string_value='COORDINATOR'))
            result = PendingProjectService(session).list_pending_projects(filter_exp=exp).get_items()
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].id, pending_project1.id)

    def test_duplicated_name_exists(self):
        p = Project(name='test')
        pending_p = PendingProject(name='test1', state=PendingProjectState.ACCEPTED)
        pending_p2 = PendingProject(name='test2', state=PendingProjectState.CLOSED)
        with db.session_scope() as session:
            session.add_all([p, pending_p, pending_p2])
            session.commit()
        with db.session_scope() as session:
            self.assertTrue(PendingProjectService(session).duplicated_name_exists(p.name))
            self.assertTrue(PendingProjectService(session).duplicated_name_exists(pending_p.name))
            self.assertFalse(PendingProjectService(session).duplicated_name_exists(pending_p2.name))
            self.assertFalse(PendingProjectService(session).duplicated_name_exists('test0'))


if __name__ == '__main__':
    unittest.main()
