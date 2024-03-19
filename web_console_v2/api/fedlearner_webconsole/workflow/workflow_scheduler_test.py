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

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, WorkflowSchedulerOutput, RunnerInput
from fedlearner_webconsole.workflow.workflow_scheduler import ScheduleWorkflowRunner
from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import _insert_schedule_workflow_item
from fedlearner_webconsole.composer.models import SchedulerItem, RunnerStatus, ItemStatus
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from testing.no_web_server_test_case import NoWebServerTestCase


class WorkflowSchedulerTest(NoWebServerTestCase):

    def test_get_workflows_need_auto_run(self):
        with db.session_scope() as session:
            template_1 = WorkflowTemplate(name='local-test', group_alias='local-test', config=b'')
            template_2 = WorkflowTemplate(name='sys-preset-nn-model', group_alias='nn', config=b'')
            session.add_all([template_1, template_2])
            session.flush()
            workflow_1 = Workflow(name='w1')
            workflow_2 = Workflow(name='w2',
                                  template_id=template_1.id,
                                  state=WorkflowState.READY,
                                  target_state=WorkflowState.INVALID)
            workflow_3 = Workflow(name='w3', template_id=template_2.id)
            workflow_5 = Workflow(name='w5',
                                  template_id=template_2.id,
                                  state=WorkflowState.READY,
                                  target_state=WorkflowState.INVALID)
            workflow_6 = Workflow(name='w6',
                                  template_id=template_2.id,
                                  state=WorkflowState.READY,
                                  target_state=WorkflowState.INVALID)
            session.add_all([workflow_1, workflow_2, workflow_3, workflow_5, workflow_6])
            session.commit()

        def fake_start_workflow(workflow_id):
            if workflow_id == workflow_6.id:
                raise RuntimeError('error workflow_6')

        with patch('fedlearner_webconsole.workflow.workflow_scheduler.start_workflow') as mock_start_workflow:
            mock_start_workflow.side_effect = fake_start_workflow
            # workflow_5 and workflow_6 will be auto-run
            runner = ScheduleWorkflowRunner()
            status, output = runner.run(RunnerContext(0, RunnerInput()))
            self.assertEqual(status, RunnerStatus.DONE)
            self.assertEqual(
                output,
                RunnerOutput(workflow_scheduler_output=WorkflowSchedulerOutput(executions=[
                    WorkflowSchedulerOutput.WorkflowExecution(id=workflow_5.id),
                    WorkflowSchedulerOutput.WorkflowExecution(id=workflow_6.id, error_message='error workflow_6'),
                ])))

    def test_insert_schedule_workflow_item(self):
        with db.session_scope() as session:
            item = SchedulerItem(name='workflow_scheduler', cron_config='* * * * * */30', status=ItemStatus.ON.value)
            session.add(item)
            session.commit()
            _insert_schedule_workflow_item(session)
            session.commit()
        with db.session_scope() as session:
            old_item = session.query(SchedulerItem).filter_by(name='workflow_scheduler').first()
            self.assertEqual(old_item.status, ItemStatus.OFF.value)
            new_item = session.query(SchedulerItem).filter_by(name='workflow_scheduler_v2').first()
            self.assertEqual(new_item.status, ItemStatus.ON.value)

    @patch('fedlearner_webconsole.workflow.workflow_scheduler.Workflow.is_local')
    def test_auto_stop(self, mock_is_local):
        mock_is_local.return_value = True
        with db.session_scope() as session:
            session.add(Project(name='test'))
            session.add(
                Job(name='testtes', state=JobState.COMPLETED, job_type=JobType.DATA_JOIN, workflow_id=30, project_id=1))

            session.add(
                Job(name='testtest', state=JobState.COMPLETED, job_type=JobType.DATA_JOIN, workflow_id=30,
                    project_id=1))
            session.add(Workflow(name='test_complete', id=30, project_id=1, state=WorkflowState.RUNNING))
            session.commit()
        output = ScheduleWorkflowRunner().auto_stop_workflows()
        self.assertEqual(output, WorkflowSchedulerOutput(executions=[WorkflowSchedulerOutput.WorkflowExecution(id=30)]))
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(30)
        self.assertEqual(workflow.state, WorkflowState.COMPLETED)
        with db.session_scope() as session:
            session.add(
                Job(name='testtes_failed',
                    state=JobState.FAILED,
                    job_type=JobType.DATA_JOIN,
                    workflow_id=31,
                    project_id=1))
            session.add(Workflow(name='test_failed', id=31, project_id=1, state=WorkflowState.RUNNING))
            session.commit()
        output = ScheduleWorkflowRunner().auto_stop_workflows()
        self.assertEqual(output, WorkflowSchedulerOutput(executions=[WorkflowSchedulerOutput.WorkflowExecution(id=31)]))
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(31)
        self.assertEqual(workflow.state, WorkflowState.FAILED)

    @patch('fedlearner_webconsole.workflow.workflow_scheduler.ScheduleWorkflowRunner.auto_run_workflows')
    @patch('fedlearner_webconsole.workflow.workflow_scheduler.ScheduleWorkflowRunner.auto_stop_workflows')
    def test_run_workflow_scheduler(self, mock_auto_stop, mock_auto_run):
        # test all succeeded
        mock_auto_run.return_value = WorkflowSchedulerOutput(
            executions=[WorkflowSchedulerOutput.WorkflowExecution(id=1)])
        mock_auto_stop.return_value = WorkflowSchedulerOutput(
            executions=[WorkflowSchedulerOutput.WorkflowExecution(id=2)])
        expected_result = (RunnerStatus.DONE,
                           RunnerOutput(workflow_scheduler_output=WorkflowSchedulerOutput(executions=[
                               WorkflowSchedulerOutput.WorkflowExecution(id=2),
                               WorkflowSchedulerOutput.WorkflowExecution(id=1)
                           ])))
        self.assertEqual(ScheduleWorkflowRunner().run(RunnerContext(1, RunnerInput())), expected_result)

        # test auto run failed
        mock_auto_stop.side_effect = Exception('Test')
        expected_result = (RunnerStatus.FAILED,
                           RunnerOutput(error_message='Test',
                                        workflow_scheduler_output=WorkflowSchedulerOutput(
                                            executions=[WorkflowSchedulerOutput.WorkflowExecution(id=1)])))
        self.assertEqual(ScheduleWorkflowRunner().run(RunnerContext(1, RunnerInput())), expected_result)
        # test all failed
        mock_auto_run.side_effect = Exception('Test')
        expected_result = (RunnerStatus.FAILED, RunnerOutput(error_message='Test Test'))
        self.assertEqual(ScheduleWorkflowRunner().run(RunnerContext(1, RunnerInput())), expected_result)


if __name__ == '__main__':
    unittest.main()
