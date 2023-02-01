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
from unittest.mock import patch, Mock

from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition, WorkflowDefinition
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.workflow.workflow_job_controller import invalidate_workflow_job
from testing.no_web_server_test_case import NoWebServerTestCase


class InvalidateWorkflowJobTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.rpc.client.RpcClient.invalidate_workflow')
    def test_invalidate_workflow_job_local(self, mock_invalidate_workflow: Mock):
        workflow_id = 777
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, project_id=1, state=WorkflowState.RUNNING)
            workflow.set_config(
                WorkflowDefinition(job_definitions=[JobDefinition(name='raw-data', is_federated=False)]))
            session.add(workflow)
            session.commit()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            invalidate_workflow_job(session, workflow)
            session.commit()
        mock_invalidate_workflow.assert_not_called()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertTrue(workflow.is_invalid())

    @patch('fedlearner_webconsole.rpc.client.RpcClient.invalidate_workflow')
    def test_invalidate_workflow_job_across_participants(self, mock_invalidate_workflow: Mock):
        workflow_id = 6789
        with db.session_scope() as session:
            project = Project(id=1)
            participant = Participant(id=123, name='testp', domain_name='fl-test.com')
            project_participant = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            session.add_all([project, participant, project_participant])

            workflow = Workflow(id=workflow_id, project_id=1, state=WorkflowState.RUNNING, uuid='test_uuid')
            workflow.set_config(
                WorkflowDefinition(job_definitions=[JobDefinition(name='data-join', is_federated=True)]))
            session.add(workflow)
            session.commit()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            invalidate_workflow_job(session, workflow)
            session.commit()
        mock_invalidate_workflow.assert_called_once_with('test_uuid')
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertTrue(workflow.is_invalid())


if __name__ == '__main__':
    unittest.main()
