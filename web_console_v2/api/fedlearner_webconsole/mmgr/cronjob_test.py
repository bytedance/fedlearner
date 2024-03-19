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
from unittest.mock import patch
from google.protobuf.struct_pb2 import Value

from testing.common import NoWebServerTestCase

from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.mmgr.cronjob import ModelTrainingCronJob
from fedlearner_webconsole.mmgr.models import ModelJobGroup, ModelJob
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.composer_pb2 import ModelTrainingCronJobInput, RunnerInput
from fedlearner_webconsole.proto.service_pb2 import GetModelJobGroupResponse
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition


def _get_workflow_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        job_definitions=[JobDefinition(name='nn-model', variables=[Variable(name='load_model_name')])])


class ModelTrainingCronJobTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=2, name='project')
        party = Participant(id=3, name='test', domain_name='fl-test.com')
        relationship = ProjectParticipant(project_id=2, participant_id=3)
        job = Job(id=1,
                  name='uuid-nn-model',
                  job_type=JobType.NN_MODEL_TRANINING,
                  state=JobState.COMPLETED,
                  workflow_id=1,
                  project_id=2)
        workflow = Workflow(id=1, name='workflow', uuid='uuid', state=WorkflowState.COMPLETED, project_id=2)
        model_job = ModelJob(name='group-v1', workflow_uuid=workflow.uuid, job_name=job.name, group_id=1, project_id=2)
        group = ModelJobGroup(id=1, name='group', uuid='uuid', latest_version=2, project_id=2)
        group.set_config(_get_workflow_definition())
        with db.session_scope() as session:
            session.add_all([project, party, relationship, job, workflow, model_job, group])
            session.commit()

    @patch('fedlearner_webconsole.rpc.client.RpcClient.get_model_job_group')
    @patch('fedlearner_webconsole.rpc.client.RpcClient.update_model_job_group')
    @patch('fedlearner_webconsole.mmgr.controller.LaunchModelJob.run')
    def test_run(self, mock_run, mock_update_group, mock_get_group):
        context = RunnerContext(index=0,
                                input=RunnerInput(model_training_cron_job_input=ModelTrainingCronJobInput(group_id=1)))
        mock_run.return_value = True, ''
        mock_get_group.return_value = GetModelJobGroupResponse(config=_get_workflow_definition(), authorized=False)
        runner_status, runner_output = ModelTrainingCronJob().run(context)
        # fail due to peer is not authorized
        self.assertEqual(runner_status, RunnerStatus.FAILED)
        self.assertEqual(runner_output.error_message, 'party fl-test.com is not authorized for group 1')
        # succeeded
        mock_get_group.return_value = GetModelJobGroupResponse(config=_get_workflow_definition(), authorized=True)
        runner_status, runner_output = ModelTrainingCronJob().run(context)
        self.assertEqual(runner_status, RunnerStatus.DONE)
        mock_run.assert_called_with(project_id=2, group_id=1, version=3)
        config = _get_workflow_definition()
        config.job_definitions[0].variables[0].typed_value.MergeFrom(Value(string_value='uuid-nn-model'))
        config.job_definitions[0].variables[0].value = 'uuid-nn-model'
        mock_update_group.assert_called_with(config=config, model_job_group_uuid='uuid')
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).get(1)
            self.assertEqual(group.latest_version, 3)
            self.assertEqual(group.get_config(), config)


if __name__ == '__main__':
    unittest.main()
