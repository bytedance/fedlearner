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
from concurrent import futures
from unittest.mock import patch, MagicMock

import grpc
from google.protobuf.empty_pb2 import Empty

from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import PendingProjectState, PendingProject, ProjectRole, Project
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.proto.rpc.v2 import project_service_pb2_grpc
from fedlearner_webconsole.proto.rpc.v2.project_service_pb2 import CreatePendingProjectRequest, \
    SyncPendingProjectStateRequest, UpdatePendingProjectRequest, CreateProjectRequest, DeletePendingProjectRequest, \
    SendTemplateRevisionRequest
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.review import common
from fedlearner_webconsole.rpc.v2.project_service_server import ProjectGrpcService, _is_same_participants
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.workflow_template.models import WorkflowTemplateKind, WorkflowTemplate, \
    WorkflowTemplateRevision
from testing.no_web_server_test_case import NoWebServerTestCase


class ProjectServiceTest(NoWebServerTestCase):
    LISTEN_PORT = 2001

    def setUp(self):
        super().setUp()
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        project_service_pb2_grpc.add_ProjectServiceServicer_to_server(ProjectGrpcService(), self._server)
        self._server.add_insecure_port(f'[::]:{self.LISTEN_PORT}')
        self._server.start()
        self._channel = grpc.insecure_channel(target=f'localhost:{self.LISTEN_PORT}')
        self._stub = project_service_pb2_grpc.ProjectServiceStub(self._channel)
        self.participants_map = {
            'test':
                ParticipantInfo(name='test', state=PendingProjectState.ACCEPTED.name,
                                role=ProjectRole.COORDINATOR.name),
            'part1':
                ParticipantInfo(name='part', state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name),
            'part2':
                ParticipantInfo(name='part', state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name)
        }

    def tearDown(self):
        self._channel.close()
        self._server.stop(5)
        return super().tearDown()

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.get_ticket_helper')
    def test_create_pending_project(self, mock_get_ticket_helper):
        participants_info = ParticipantsInfo(
            participants_map={
                'test':
                    ParticipantInfo(
                        name='test', state=PendingProjectState.ACCEPTED.name, role=ProjectRole.COORDINATOR.name),
                'part':
                    ParticipantInfo(
                        name='part', state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name)
            })
        request = CreatePendingProjectRequest(name='test-project',
                                              uuid='test',
                                              participants_info=participants_info,
                                              ticket_uuid=common.NO_CENTRAL_SERVER_UUID)
        mock_get_ticket_helper.return_value.validate_ticket.return_value = True
        resp = self._stub.CreatePendingProject(request, None)
        with db.session_scope() as session:
            pending_project: PendingProject = session.query(PendingProject).filter_by(uuid='test').first()
            self.assertEqual(resp, Empty())
            self.assertEqual(pending_project.state, PendingProjectState.PENDING)
            self.assertEqual(pending_project.role, ProjectRole.PARTICIPANT)
            self.assertEqual(pending_project.get_participants_info(), participants_info)
            self.assertEqual(pending_project.ticket_status, TicketStatus.APPROVED)
            self.assertEqual(pending_project.ticket_uuid, common.NO_CENTRAL_SERVER_UUID)

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.get_ticket_helper')
    def test_create_pending_project_ticket_wrong(self, mock_get_ticket_helper):
        mock_get_ticket_helper.return_value.validate_ticket.return_value = False
        participants_info = ParticipantsInfo(
            participants_map={
                'test':
                    ParticipantInfo(
                        name='test', state=PendingProjectState.ACCEPTED.name, role=ProjectRole.COORDINATOR.name),
                'part':
                    ParticipantInfo(
                        name='part', state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name)
            })
        request = CreatePendingProjectRequest(name='test-project',
                                              uuid='test',
                                              participants_info=participants_info,
                                              ticket_uuid='wrong')
        with self.assertRaisesRegex(grpc.RpcError, 'ticket wrong is not validated') as cm:
            self._stub.CreatePendingProject(request, None)
            self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
        with db.session_scope() as session:
            pending_project: PendingProject = session.query(PendingProject).filter_by(uuid='test').first()
            self.assertIsNone(pending_project)

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.get_pure_domain_from_context')
    def test_update_pending_project(self, mock_pure_domain):
        participants_map = self.participants_map
        participants_info = ParticipantsInfo(participants_map=participants_map)
        pending_project = PendingProject(uuid='unique1',
                                         name='test',
                                         state=PendingProjectState.PENDING,
                                         role=ProjectRole.PARTICIPANT)
        pending_project.set_participants_info(participants_info)
        with db.session_scope() as session:
            session.add(pending_project)
            session.commit()
        mock_pure_domain.return_value = 'wrong coordinator'
        participants_map['part2'].state = PendingProjectState.ACCEPTED.name
        with self.assertRaisesRegex(grpc.RpcError,
                                    'wrong coordinator is not coordinator in pending project unique1') as cm:
            self._stub.UpdatePendingProject(
                UpdatePendingProjectRequest(uuid=pending_project.uuid, participants_map=participants_map))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
        mock_pure_domain.return_value = 'test'
        resp = self._stub.UpdatePendingProject(
            UpdatePendingProjectRequest(uuid=pending_project.uuid, participants_map=participants_map))
        with db.session_scope() as session:
            self.assertEqual(resp, Empty())
            result: PendingProject = session.query(PendingProject).get(pending_project.id)
            self.assertEqual(result.get_participants_info(), ParticipantsInfo(participants_map=participants_map))

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.get_pure_domain_from_context')
    def test_sync_pending_project_state(self, mock_pure_domain):
        # test participant sync to coordinator
        participants_info = ParticipantsInfo(participants_map=self.participants_map)
        pending_project = PendingProject(uuid='unique2',
                                         name='test',
                                         state=PendingProjectState.ACCEPTED,
                                         role=ProjectRole.COORDINATOR)
        pending_project.set_participants_info(participants_info)
        with db.session_scope() as session:
            session.add(pending_project)
            session.commit()
        mock_pure_domain.return_value = 'part1'
        resp = self._stub.SyncPendingProjectState(
            SyncPendingProjectStateRequest(uuid=pending_project.uuid, state='ACCEPTED'))
        with db.session_scope() as session:
            self.assertEqual(resp, Empty())
            result: PendingProject = session.query(PendingProject).get(pending_project.id)
            participants_info.participants_map['part1'].state = PendingProjectState.ACCEPTED.name
            self.assertEqual(result.get_participants_info(), participants_info)

    def test_is_same_participants(self):
        self.assertFalse(
            _is_same_participants(self.participants_map, {
                'test': ParticipantInfo(),
                'part1': ParticipantInfo(),
                'part2': ParticipantInfo()
            }))
        self.assertTrue(
            _is_same_participants(self.participants_map, {
                'test': ParticipantInfo(),
                'part1': ParticipantInfo(),
                'part3': ParticipantInfo()
            }))

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.PendingProjectService.create_project_locally')
    def test_create_project(self, mock_create: MagicMock):
        with db.session_scope() as session:
            pending_project1 = PendingProject(uuid='test1',
                                              id=1,
                                              name='test project',
                                              state=PendingProjectState.ACCEPTED)
            pending_project2 = PendingProject(uuid='pending',
                                              id=2,
                                              name='test project 2',
                                              state=PendingProjectState.PENDING)
            pending_project3 = PendingProject(uuid='dup',
                                              id=3,
                                              name='test project 3',
                                              state=PendingProjectState.ACCEPTED)
            project = Project(name='test project 3')
            session.add_all([pending_project1, pending_project2, pending_project3, project])
            session.commit()
        # successful
        resp = self._stub.CreateProject(CreateProjectRequest(uuid='test1'))
        self.assertEqual(resp, Empty())
        mock_create.assert_called_once_with('test1')
        # fail due to pending project not found
        with self.assertRaisesRegex(grpc.RpcError, 'failed to find pending project, uuid is nothing') as cm:
            self._stub.CreateProject(CreateProjectRequest(uuid='nothing'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.NOT_FOUND)
            mock_create.assert_not_called()
        # fail due to state not valid
        with self.assertRaisesRegex(grpc.RpcError, 'pending pending project has not been accepted') as cm:
            self._stub.CreateProject(CreateProjectRequest(uuid='pending'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
            mock_create.assert_not_called()
        # fail due to name duplicate
        with self.assertRaisesRegex(grpc.RpcError, 'test project 3 project has already existed, uuid is dup') as cm:
            self._stub.CreateProject(CreateProjectRequest(uuid='dup'))
            self.assertEqual(cm.exception.code(), grpc.StatusCode.ALREADY_EXISTS)
            mock_create.assert_not_called()

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.get_pure_domain_from_context')
    def test_delete_pending_project(self, mock_pure_domain: MagicMock):
        with db.session_scope() as session:
            pending_project1 = PendingProject(uuid='test1',
                                              id=1,
                                              name='test project',
                                              state=PendingProjectState.ACCEPTED)
            pending_project1.set_participants_info(ParticipantsInfo(participants_map=self.participants_map))
            session.add(pending_project1)
            session.commit()
        mock_pure_domain.return_value = 'part1'
        with self.assertRaisesRegex(grpc.RpcError, 'part1 is not coordinator in pending project test1') as cm:
            self._stub.DeletePendingProject(DeletePendingProjectRequest(uuid='test1'))
        self.assertEqual(cm.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
        mock_pure_domain.return_value = 'test'
        resp = self._stub.DeletePendingProject(DeletePendingProjectRequest(uuid='test1'))
        self.assertEqual(resp, Empty())
        with db.session_scope() as session:
            self.assertIsNone(session.query(PendingProject).get(pending_project1.id))
        resp = self._stub.DeletePendingProject(DeletePendingProjectRequest(uuid='test1'))
        self.assertEqual(resp, Empty())

    @patch('fedlearner_webconsole.rpc.v2.project_service_server.get_pure_domain_from_context')
    def test_send_template_revision(self, mock_pure_domain: MagicMock):
        mock_pure_domain.return_value = 'a'
        self._stub.SendTemplateRevision(
            SendTemplateRevisionRequest(config=WorkflowDefinition(group_alias='test'),
                                        name='test',
                                        revision_index=2,
                                        comment='test comment',
                                        kind=WorkflowTemplateKind.PEER.name))
        self._stub.SendTemplateRevision(
            SendTemplateRevisionRequest(config=WorkflowDefinition(group_alias='test', variables=[Variable()]),
                                        name='test',
                                        revision_index=3,
                                        comment='test comment',
                                        kind=WorkflowTemplateKind.PEER.name))
        self._stub.SendTemplateRevision(
            SendTemplateRevisionRequest(config=WorkflowDefinition(group_alias='test'),
                                        name='test',
                                        revision_index=1,
                                        comment='test comment',
                                        kind=WorkflowTemplateKind.PEER.name))
        with db.session_scope() as session:
            tpl = session.query(WorkflowTemplate).filter_by(name='test').first()
            self.assertEqual(tpl.get_config(), WorkflowDefinition(group_alias='test', variables=[Variable()]))
            self.assertEqual(tpl.coordinator_pure_domain_name, 'a')
            self.assertEqual(tpl.kind, 2)
            revisions = session.query(WorkflowTemplateRevision).filter_by(template_id=tpl.id).all()
            self.assertEqual(sorted([r.revision_index for r in revisions]), [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
