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
from datetime import datetime, timezone

from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant, ParticipantType
from fedlearner_webconsole.project.models import Project, PendingProject, PendingProjectState, ProjectRole
from fedlearner_webconsole.proto import project_pb2
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.project_pb2 import ProjectConfig, ProjectRef, ParticipantInfo, \
    PendingProjectPb, ParticipantsInfo
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from testing.no_web_server_test_case import NoWebServerTestCase


class ProjectTest(NoWebServerTestCase):

    def test_set_and_get_variables(self):
        config = ProjectConfig(variables=[
            Variable(name='old_var', value='old', access_mode=Variable.PEER_READABLE),
        ])
        with db.session_scope() as session:
            project = Project(id=111, config=config.SerializeToString())
            session.add(project)
            session.commit()
            self.assertEqual(len(project.get_variables()), 1)
            self.assertEqual(project.get_variables()[0].name, 'old_var')
            project.set_variables([Variable(name='new_var', value='new', access_mode=Variable.PEER_WRITABLE)])
            session.commit()
        with db.session_scope() as session:
            project = session.query(Project).get(111)
            self.assertEqual(len(project.get_variables()), 1)
            self.assertEqual(project.get_variables()[0].name, 'new_var')

    def test_get_storage_root_path(self):
        project = Project(id=111)
        self.assertEqual(project.get_storage_root_path('not found'), 'not found')
        project.set_variables(
            [Variable(name='storage_root_path', value='root path', access_mode=Variable.PEER_READABLE)])
        self.assertEqual(project.get_storage_root_path('not found'), 'root path')

    def test_to_ref(self):
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        project_id = 66666
        participant_id = 2
        with db.session_scope() as session:
            project = Project(id=project_id, name='test project', creator='test_user', created_at=created_at)
            participant = Participant(id=participant_id, name='test part', domain_name='fl-test.com')
            relation = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            session.add_all([project, participant, relation])
            session.commit()
        with db.session_scope() as session:
            project = session.query(Project).get(project_id)
            participant = session.query(Participant).get(participant_id)
            self.assertEqual(
                project.to_ref(),
                ProjectRef(id=project_id,
                           name='test project',
                           creator='test_user',
                           participant_type='PLATFORM',
                           created_at=int(created_at.timestamp()),
                           participants=[participant.to_proto()],
                           participants_info=ParticipantsInfo(),
                           role=ProjectRole.PARTICIPANT.name),
            )

    def test_to_proto(self):
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        project_id = 12356
        participant_id = 22
        variable = Variable(name='test_var', access_mode=Variable.PEER_READABLE, typed_value=Value(string_value='jjjj'))
        with db.session_scope() as session:
            project = Project(id=project_id,
                              name='test project',
                              creator='test_user',
                              created_at=created_at,
                              comment='test comment',
                              token='test token')
            project.set_variables([variable])
            participant = Participant(id=participant_id, name='test part', domain_name='fl-test.com')
            relation = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            participants_info = ParticipantsInfo(participants_map={'test': ParticipantInfo(name='test part')})
            project.set_participants_info(participants_info)
            session.add_all([project, participant, relation])
            session.commit()
        with db.session_scope() as session:
            project = session.query(Project).get(project_id)
            participant = session.query(Participant).get(participant_id)
            actual = project.to_proto()
            self.assertEqual(
                actual,
                project_pb2.Project(id=project_id,
                                    name='test project',
                                    token='test token',
                                    comment='test comment',
                                    creator='test_user',
                                    participant_type='PLATFORM',
                                    created_at=int(created_at.timestamp()),
                                    updated_at=actual.updated_at,
                                    variables=[variable],
                                    participants=[participant.to_proto()],
                                    participants_info=participants_info,
                                    config=ProjectConfig(variables=[variable]),
                                    role=ProjectRole.PARTICIPANT.name),
            )


class PendingProjectTest(NoWebServerTestCase):

    def test_to_proto(self):
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
        pending_proj.set_config(ProjectConfig())
        participants_infos = ParticipantsInfo(
            participants_map={'test': ParticipantInfo(name='test', role=PendingProjectState.ACCEPTED.name)})
        pending_proj.set_participants_info(participants_infos)
        self.assertEqual(
            pending_proj.to_proto(),
            PendingProjectPb(id=123,
                             name='test',
                             uuid='uuid',
                             state=PendingProjectState.ACCEPTED.name,
                             role=ProjectRole.PARTICIPANT.name,
                             comment='test',
                             created_at=1652140800,
                             updated_at=1652140800,
                             config=ProjectConfig(),
                             participants_info=participants_infos,
                             ticket_status=TicketStatus.PENDING.name,
                             participant_type=ParticipantType.LIGHT_CLIENT.name))

    def test_get_participant_info(self):
        pending_proj = PendingProject(id=123, name='test', uuid='uuid')
        pending_proj.set_config(ProjectConfig())
        participants_infos = ParticipantsInfo(participants_map={'test': ParticipantInfo(name='test')})
        pending_proj.set_participants_info(participants_infos)
        self.assertEqual(pending_proj.get_participant_info('test'), ParticipantInfo(name='test'))
        self.assertEqual(pending_proj.get_participant_info('test1'), None)

    def test_get_coordinator_info(self):
        pending_proj = PendingProject(id=123, name='test', uuid='uuid')
        pending_proj.set_config(ProjectConfig())
        participants_infos = ParticipantsInfo(
            participants_map={'test': ParticipantInfo(name='test', role=ProjectRole.COORDINATOR.name)})
        pending_proj.set_participants_info(participants_infos)
        self.assertEqual(pending_proj.get_coordinator_info(),
                         ('test', ParticipantInfo(name='test', role=ProjectRole.COORDINATOR.name)))
        pending_proj.set_participants_info(ParticipantsInfo())
        with self.assertRaises(ValueError):
            pending_proj.get_coordinator_info()

    def test_get_participant_type(self):
        pending_proj = PendingProject(id=123, name='test', uuid='uuid')
        participants_infos = ParticipantsInfo(participants_map={
            'test': ParticipantInfo(name='test', role=ProjectRole.PARTICIPANT.name, type=ParticipantType.PLATFORM.name)
        })
        pending_proj.set_participants_info(participants_infos)
        self.assertEqual(pending_proj.get_participant_type(), ParticipantType.PLATFORM.name)


if __name__ == '__main__':
    unittest.main()
