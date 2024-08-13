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
import unittest
from unittest.mock import patch, MagicMock
from google.protobuf.json_format import ParseDict
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.proto.common_pb2 import CreateJobFlag
from fedlearner_webconsole.proto.service_pb2 import GetWorkflowResponse
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition, \
    WorkflowDefinition
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow.utils import \
    is_peer_job_inheritance_matched, is_local


class UtilsTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=0)

        with db.session_scope() as session:
            session.add(project)
            session.commit()

    def test_is_local(self):
        config = {
            'job_definitions': [
                {
                    'name': 'raw-data',
                    'is_federated': False
                },
                {
                    'name': 'raw-data',
                    'is_federated': True
                },
            ]
        }
        config = ParseDict(config, WorkflowDefinition())
        self.assertFalse(is_local(config))
        job_flags = [CreateJobFlag.NEW, CreateJobFlag.NEW]
        self.assertFalse(is_local(config, job_flags))
        job_flags = [CreateJobFlag.NEW, CreateJobFlag.REUSE]
        self.assertTrue(is_local(config, job_flags))
        job_flags = [CreateJobFlag.REUSE, CreateJobFlag.REUSE]
        self.assertTrue(is_local(config, job_flags))

    @patch('fedlearner_webconsole.rpc.client.RpcClient' '.from_project_and_participant')
    def test_is_peer_job_inheritance_matched(self, mock_rpc_client_factory):
        # Mock RPC
        peer_job_0 = JobDefinition(name='raw-data-job')
        peer_job_1 = JobDefinition(name='train-job', is_federated=True)
        peer_config = WorkflowDefinition(job_definitions=[peer_job_0, peer_job_1])
        resp = GetWorkflowResponse(config=peer_config)
        mock_rpc_client = MagicMock()
        mock_rpc_client.get_workflow = MagicMock(return_value=resp)
        mock_rpc_client_factory.return_value = mock_rpc_client

        job_0 = JobDefinition(name='train-job', is_federated=True)
        workflow_definition = WorkflowDefinition(job_definitions=[job_0])

        participant = Participant(domain_name='fl-test.com')

        project = Project(name='test-project', token='test-token')
        parent_workflow = Workflow(project=project, uuid='workflow-uuid-0000', name='workflow-0')
        self.assertTrue(
            is_peer_job_inheritance_matched(project=project,
                                            workflow_definition=workflow_definition,
                                            job_flags=[CreateJobFlag.REUSE],
                                            peer_job_flags=[CreateJobFlag.NEW, CreateJobFlag.REUSE],
                                            parent_uuid=parent_workflow.uuid,
                                            parent_name=parent_workflow.name,
                                            participants=[participant]))
        mock_rpc_client.get_workflow.assert_called_once_with(parent_workflow.uuid, parent_workflow.name)
        mock_rpc_client_factory.assert_called_once()
        args, kwargs = mock_rpc_client_factory.call_args_list[0]
        # Comparing call args one by one because message list
        # can not compare directly
        self.assertEqual(len(args), 3)
        self.assertEqual(args[0], 'test-project')
        self.assertEqual(args[1], 'test-token')
        self.assertEqual(args[2], 'fl-test.com')

        self.assertFalse(
            is_peer_job_inheritance_matched(project=project,
                                            workflow_definition=workflow_definition,
                                            job_flags=[CreateJobFlag.NEW],
                                            peer_job_flags=[CreateJobFlag.NEW, CreateJobFlag.REUSE],
                                            parent_uuid=parent_workflow.uuid,
                                            parent_name=parent_workflow.name,
                                            participants=[participant]))


if __name__ == '__main__':
    unittest.main()
