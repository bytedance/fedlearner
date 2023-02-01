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

import grpc
import grpc_testing
from google.protobuf.empty_pb2 import Empty
from google.protobuf.descriptor import ServiceDescriptor

from fedlearner_webconsole.project.models import PendingProject, PendingProjectState, ProjectRole
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.proto.rpc.v2.project_service_pb2 import CreatePendingProjectRequest, \
    UpdatePendingProjectRequest, SyncPendingProjectStateRequest, CreateProjectRequest, DeletePendingProjectRequest, \
    SendTemplateRevisionRequest
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.proto.rpc.v2 import project_service_pb2
from fedlearner_webconsole.rpc.v2.project_service_client import ProjectServiceClient
from fedlearner_webconsole.workflow_template.models import WorkflowTemplateKind
from testing.rpc.client import RpcClientTestCase

_SERVER_DESCRIPTOR: ServiceDescriptor = project_service_pb2.DESCRIPTOR.services_by_name['ProjectService']


class ProjectServiceClientTest(RpcClientTestCase):

    def setUp(self):
        super().setUp()
        self._fake_channel: grpc_testing.Channel = grpc_testing.channel([_SERVER_DESCRIPTOR],
                                                                        grpc_testing.strict_real_time())
        self._client = ProjectServiceClient(self._fake_channel)

    def test_create_pending_project(self):
        pending_project = PendingProject(uuid='test', name='test-project', ticket_uuid='test')

        participants_info = ParticipantsInfo(
            participants_map={
                'test':
                    ParticipantInfo(
                        name='test', state=PendingProjectState.ACCEPTED.name, role=ProjectRole.COORDINATOR.name),
                'part':
                    ParticipantInfo(
                        name='part', state=PendingProjectState.PENDING.name, role=ProjectRole.PARTICIPANT.name)
            })
        pending_project.set_participants_info(participants_info)
        call = self.client_execution_pool.submit(self._client.create_pending_project, pending_project=pending_project)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['CreatePendingProject'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            CreatePendingProjectRequest(uuid='test',
                                        participants_info=participants_info,
                                        name='test-project',
                                        config=pending_project.get_config(),
                                        ticket_uuid='test'))
        self.assertEqual(call.result(), expected_response)

    def test_update_pending_project(self):
        participants_map = {
            'part':
                ParticipantInfo(name='part', state=PendingProjectState.ACCEPTED.name, role=ProjectRole.PARTICIPANT.name)
        }

        call = self.client_execution_pool.submit(self._client.update_pending_project,
                                                 uuid='test',
                                                 participants_map=participants_map)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['UpdatePendingProject'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, UpdatePendingProjectRequest(uuid='test', participants_map=participants_map))
        self.assertEqual(call.result(), expected_response)

    def test_sync_pending_project_state(self):
        call = self.client_execution_pool.submit(self._client.sync_pending_project_state,
                                                 uuid='test',
                                                 state=PendingProjectState.ACCEPTED)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['SyncPendingProjectState'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, SyncPendingProjectStateRequest(uuid='test', state='ACCEPTED'))
        self.assertEqual(call.result(), expected_response)

    def test_create_project(self):
        call = self.client_execution_pool.submit(self._client.create_project, uuid='test')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['CreateProject'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, CreateProjectRequest(uuid='test'))
        self.assertEqual(call.result(), expected_response)

    def test_delete_pending_project(self):
        call = self.client_execution_pool.submit(self._client.delete_pending_project, uuid='test')
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['DeletePendingProject'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(request, DeletePendingProjectRequest(uuid='test'))
        self.assertEqual(call.result(), expected_response)

    def test_send_template_revision(self):
        call = self.client_execution_pool.submit(self._client.send_template_revision,
                                                 config=WorkflowDefinition(),
                                                 name='test',
                                                 comment='test',
                                                 kind=WorkflowTemplateKind.PEER,
                                                 revision_index=1)
        invocation_metadata, request, rpc = self._fake_channel.take_unary_unary(
            _SERVER_DESCRIPTOR.methods_by_name['SendTemplateRevision'])
        expected_response = Empty()
        rpc.terminate(
            response=expected_response,
            code=grpc.StatusCode.OK,
            trailing_metadata=(),
            details=None,
        )
        self.assertEqual(
            request,
            SendTemplateRevisionRequest(config=WorkflowDefinition(),
                                        name='test',
                                        comment='test',
                                        kind=WorkflowTemplateKind.PEER.name,
                                        revision_index=1))
        self.assertEqual(call.result(), expected_response)


if __name__ == '__main__':
    unittest.main()
