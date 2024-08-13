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
from unittest.mock import Mock, call, patch

import grpc
from google.protobuf.empty_pb2 import Empty

from fedlearner_webconsole.participant.models import ParticipantType
from fedlearner_webconsole.project.controllers import PendingProjectRpcController, ParticipantResp, _get_domain_name
from fedlearner_webconsole.project.models import PendingProject, ProjectRole, PendingProjectState
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.rpc.v2.client_base import ParticipantRpcClient
from testing.no_web_server_test_case import NoWebServerTestCase


class FakeRpcClient(ParticipantRpcClient):

    def __init__(self):
        super().__init__(None)

    def fake_method(self, request: str, succeeded: bool = True):
        if succeeded:
            return request
        raise grpc.RpcError

    def sync_pending_project_state(self, uuid: str, state: PendingProjectState):
        del uuid, state
        return Empty()


class ProjectControllerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.pending_project = PendingProject(id=1, role=ProjectRole.COORDINATOR)
        self.pending_project.set_participants_info(
            ParticipantsInfo(
                participants_map={
                    'coordinator': ParticipantInfo(role=ProjectRole.COORDINATOR.name),
                    'part1': ParticipantInfo(role=ProjectRole.PARTICIPANT.name),
                    'part2': ParticipantInfo(role=ProjectRole.PARTICIPANT.name),
                    'part3': ParticipantInfo(role=ProjectRole.PARTICIPANT.name, type=ParticipantType.LIGHT_CLIENT.name),
                }))

    @patch('fedlearner_webconsole.project.controllers.ProjectServiceClient.from_participant')
    def test_send_to_all(self, mock_from_participant: Mock):
        mock_from_participant.return_value = FakeRpcClient()
        result = PendingProjectRpcController(
            self.pending_project).send_to_participants(lambda client: FakeRpcClient.fake_method(client, request='test'))
        mock_from_participant.assert_has_calls([call('fl-part1.com'), call('fl-part2.com')], any_order=True)
        self.assertEqual(mock_from_participant.call_count, 2)
        self.assertEqual(
            result, {
                'part1': ParticipantResp(succeeded=True, resp='test', msg=''),
                'part2': ParticipantResp(succeeded=True, resp='test', msg='')
            })
        # Failed case
        result = PendingProjectRpcController(self.pending_project).send_to_participants(
            lambda client: client.fake_method(request='test', succeeded=False))
        self.assertEqual(
            result, {
                'part1': ParticipantResp(succeeded=False, resp=Empty(), msg=''),
                'part2': ParticipantResp(succeeded=False, resp=Empty(), msg='')
            })

    @patch('fedlearner_webconsole.project.controllers.ProjectServiceClient.from_participant')
    @patch('fedlearner_webconsole.project.controllers.ProjectServiceClient.sync_pending_project_state',
           FakeRpcClient.sync_pending_project_state)
    def test_send_to_coordinator(self, mock_from_participant: Mock):
        mock_from_participant.return_value = FakeRpcClient()
        self.pending_project.role = ProjectRole.PARTICIPANT
        result = PendingProjectRpcController(self.pending_project).sync_pending_project_state_to_coordinator(
            uuid='test', state=PendingProjectState.ACCEPTED)
        mock_from_participant.assert_called_once_with('fl-coordinator.com')
        self.assertEqual(result, ParticipantResp(succeeded=True, resp=Empty(), msg=''))

    def test_get_domain_name(self):
        self.assertEqual(_get_domain_name('bytedance'), 'fl-bytedance.com')


if __name__ == '__main__':
    unittest.main()
