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

from unittest.mock import patch, MagicMock

from google.protobuf.empty_pb2 import Empty

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.controllers import ParticipantResp
from fedlearner_webconsole.project.models import PendingProject, ProjectRole, PendingProjectState
from fedlearner_webconsole.project.project_scheduler import ScheduleProjectRunner, _get_ids_needed_schedule,\
    _if_pending_project_needed_create, _if_all_participants_closed
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, RunnerOutput, PendingProjectSchedulerOutput
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from testing.no_web_server_test_case import NoWebServerTestCase


class ProjectSchedulerTest(NoWebServerTestCase):

    def test_get_ids_needed_schedule(self):
        p1 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        p2 = PendingProject(uuid='b',
                            role=ProjectRole.PARTICIPANT,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        p3 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.CLOSED)
        with db.session_scope() as session:
            session.add(p1)
            session.add(p2)
            session.add(p3)
            session.commit()
        with db.session_scope() as session:
            self.assertEqual(_get_ids_needed_schedule(session), [p1.id])  # pylint: disable=protected-access

    def test_if_pending_project_needed_create(self):
        p = PendingProject()

        # Test case: all accepted
        part_infos = ParticipantsInfo(
            participants_map={
                'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.PARTICIPANT.name),
                'b': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.PARTICIPANT.name)
            })
        p.set_participants_info(part_infos)
        self.assertEqual(_if_pending_project_needed_create(p), True)

        # Test case: one rejected one accepted
        part_infos = ParticipantsInfo(
            participants_map={
                'a': ParticipantInfo(state=PendingProjectState.CLOSED.name, role=ProjectRole.PARTICIPANT.name),
                'b': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.PARTICIPANT.name)
            })
        p.set_participants_info(part_infos)
        self.assertEqual(_if_pending_project_needed_create(p), True)

        # Test case: one pending one accepted
        part_infos = ParticipantsInfo(
            participants_map={
                'a': ParticipantInfo(state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name),
                'b': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.PARTICIPANT.name)
            })
        p.set_participants_info(part_infos)
        self.assertEqual(_if_pending_project_needed_create(p), False)

    def test_if_all_participants_closed(self):
        p = PendingProject()
        only_coordinator = ParticipantsInfo(participants_map={
            'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.COORDINATOR.name),
        })
        p.set_participants_info(only_coordinator)
        self.assertEqual(_if_all_participants_closed(p), False)

        part_all_accepted = ParticipantsInfo(
            participants_map={
                'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.COORDINATOR.name),
                'b': ParticipantInfo(state=PendingProjectState.CLOSED.name, role=ProjectRole.PARTICIPANT.name),
                'c': ParticipantInfo(state=PendingProjectState.CLOSED.name, role=ProjectRole.PARTICIPANT.name),
            })
        p.set_participants_info(part_all_accepted)
        self.assertEqual(_if_all_participants_closed(p), True)
        part_infos_one_pending = ParticipantsInfo(
            participants_map={
                'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.COORDINATOR.name),
                'b': ParticipantInfo(state=PendingProjectState.CLOSED.name, role=ProjectRole.PARTICIPANT.name),
                'c': ParticipantInfo(state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name),
            })
        p.set_participants_info(part_infos_one_pending)
        self.assertEqual(_if_all_participants_closed(p), False)

    @patch('fedlearner_webconsole.project.project_scheduler.PendingProjectRpcController.send_to_participants')
    def test_create_pending_project(self, mock_sent: MagicMock):
        p1 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        with db.session_scope() as session:
            session.add(p1)
            session.commit()
        result = ScheduleProjectRunner()._create_pending_project([p1.id])  # pylint: disable=protected-access
        mock_sent.assert_called_once()
        self.assertEqual(result, [p1.id])

    @patch('fedlearner_webconsole.project.project_scheduler.PendingProjectRpcController.send_to_participants')
    def test_sync_all_participants(self, mock_sent: MagicMock):
        p1 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        with db.session_scope() as session:
            session.add(p1)
            session.commit()
        result = ScheduleProjectRunner()._update_all_participants([p1.id])  # pylint: disable=protected-access
        mock_sent.assert_called_once()
        self.assertEqual(result, [p1.id])

    @patch('fedlearner_webconsole.project.project_scheduler.PendingProjectRpcController.send_to_participants')
    @patch('fedlearner_webconsole.project.project_scheduler.PendingProjectService.create_project_locally')
    def test_create_project(self, mock_create: MagicMock, mock_sent: MagicMock):
        p1 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        p3 = PendingProject(uuid='c',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        part_infos = ParticipantsInfo(
            participants_map={
                'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name),
                'b': ParticipantInfo(state=PendingProjectState.ACCEPTED.name)
            })
        p1.set_participants_info(part_infos)
        p3.set_participants_info(
            ParticipantsInfo(
                participants_map={
                    'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name),
                    'b': ParticipantInfo(state=PendingProjectState.PENDING.name)
                }))
        with db.session_scope() as session:
            session.add(p1)
            session.add(p3)
            session.commit()
        mock_sent.return_value = {
            'a': ParticipantResp(succeeded=True, resp=Empty(), msg=''),
            'b': ParticipantResp(succeeded=True, resp=Empty(), msg='')
        }
        result = ScheduleProjectRunner()._create_project([p1.id, p3.id])  # pylint: disable=protected-access
        mock_sent.assert_called_once()
        mock_create.assert_called_once_with(p1.uuid)
        self.assertEqual(result, [p1.uuid])

    def test_fail_project(self):
        p1 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        p2 = PendingProject(uuid='b',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        part_infos = ParticipantsInfo(participants_map={
            'a': ParticipantInfo(state=PendingProjectState.ACCEPTED.name, role=ProjectRole.PARTICIPANT.name),
        })
        p1.set_participants_info(part_infos)
        part_infos = ParticipantsInfo(participants_map={
            'a': ParticipantInfo(state=PendingProjectState.CLOSED.name, role=ProjectRole.PARTICIPANT.name),
        })
        p2.set_participants_info(part_infos)
        with db.session_scope() as session:
            session.add(p1)
            session.add(p2)
            session.commit()
        result = ScheduleProjectRunner()._fail_pending_project([p1.id, p2.id])  # pylint: disable=protected-access
        self.assertEqual(result, [p2.id])
        with db.session_scope() as session:
            p2 = session.query(PendingProject).get(p2.id)
            self.assertEqual(p2.state, PendingProjectState.FAILED)

    def test_run(self):
        p1 = PendingProject(uuid='a',
                            role=ProjectRole.COORDINATOR,
                            ticket_status=TicketStatus.APPROVED,
                            state=PendingProjectState.ACCEPTED)
        with db.session_scope() as session:
            session.add(p1)
            session.commit()
        result: RunnerOutput = ScheduleProjectRunner().run(RunnerContext(1, RunnerInput()))
        self.assertEqual(result[0], RunnerStatus.DONE)
        self.assertEqual(
            result[1].pending_project_scheduler_output,
            PendingProjectSchedulerOutput(pending_project_created_ids=[p1.id],
                                          pending_project_updated_ids=[p1.id],
                                          projects_created_uuids=[p1.uuid]))
