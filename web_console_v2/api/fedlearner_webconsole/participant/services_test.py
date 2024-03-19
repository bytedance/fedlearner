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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant, ParticipantType, ProjectParticipant
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.pp_time import sleep
from testing.no_web_server_test_case import NoWebServerTestCase


class ParticipantServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.participant_1 = Participant(name='participant 1', domain_name='fl-participant-1.com')
        self.participant_2 = Participant(name='participant 2', domain_name='participant-2.fedlearner.net')
        self.participant_3 = Participant(name='participant 3',
                                         domain_name='participant-3.fedlearner.net',
                                         type=ParticipantType.LIGHT_CLIENT)
        self.project_1 = Project(name='project 1')
        self.project_2 = Project(name='project 2')
        self.project_3 = Project(name='project 3')
        self.relationship_11 = ProjectParticipant(project_id=1, participant_id=1)
        self.relationship_12 = ProjectParticipant(project_id=1, participant_id=2)
        self.relationship_22 = ProjectParticipant(project_id=2, participant_id=2)
        self.relationship_33 = ProjectParticipant(project_id=3, participant_id=3)

        with db.session_scope() as session:
            session.add(self.participant_1)
            session.flush()
            sleep(1)
            session.add(self.participant_2)
            session.add(self.project_1)
            session.flush()
            sleep(1)
            session.add(self.project_2)
            session.add(self.project_3)
            session.add(self.participant_3)
            session.add(self.relationship_11)
            session.add(self.relationship_12)
            session.add(self.relationship_22)
            session.add(self.relationship_33)
            session.commit()

    def test_get_participant_by_pure_domain_name(self):
        with db.session_scope() as session:
            service = ParticipantService(session)

            p = service.get_participant_by_pure_domain_name('participant-1')
            self.assertEqual(p.id, self.participant_1.id)
            p = service.get_participant_by_pure_domain_name('participant-2')
            self.assertEqual(p.id, self.participant_2.id)
            self.assertIsNone(service.get_participant_by_pure_domain_name('participant'))
            self.assertIsNone(service.get_participant_by_pure_domain_name('none'))

    def test_get_participants_by_project_id(self):
        with db.session_scope() as session:
            service = ParticipantService(session)
            participants = service.get_participants_by_project(1)
            self.assertEqual(len(participants), 2)
            self.assertEqual(participants[0].name, 'participant 2')
            self.assertEqual(participants[1].name, 'participant 1')

            participants = service.get_participants_by_project(2)
            self.assertEqual(len(participants), 1)
            self.assertEqual(participants[0].name, 'participant 2')

            participants = service.get_participants_by_project(3)
            self.assertEqual(len(participants), 1)
            self.assertEqual(participants[0].name, 'participant 3')

    def test_get_platform_participants_by_project(self):

        with db.session_scope() as session:
            service = ParticipantService(session)
            participants = service.get_platform_participants_by_project(2)
            self.assertEqual(len(participants), 1)
            self.assertEqual(participants[0].name, 'participant 2')

            participants = service.get_platform_participants_by_project(3)
            self.assertEqual(len(participants), 0)

    def test_get_number_of_projects(self):
        with db.session_scope() as session:
            service = ParticipantService(session)
            num1 = service.get_number_of_projects(1)
            self.assertEqual(num1, 1)

            num2 = service.get_number_of_projects(2)
            self.assertEqual(num2, 2)


if __name__ == '__main__':
    unittest.main()
