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
from unittest.mock import patch

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.service import WorkflowService
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.workflow.models import (Workflow, WorkflowState, TransactionState)
from fedlearner_webconsole.workflow.service import update_cronjob_config
from fedlearner_webconsole.composer.models import SchedulerItem, ItemStatus


class WorkflowServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=0)

        with db.session_scope() as session:
            session.add(project)
            session.commit()

    @patch('fedlearner_webconsole.workflow.service.YamlFormatterService.generate_job_run_yaml')
    def test_valid_workflow(self, mock_generate_job_run_yaml):
        with db.session_scope() as session:
            workflow = Workflow(id=0, project_id=99)
            session.add(workflow)
            session.flush()
            job = Job(id=0,
                      name='test-job-0',
                      job_type=JobType.RAW_DATA,
                      workflow_id=0,
                      project_id=99,
                      config=JobDefinition(name='test-job').SerializeToString())
            session.add(job)
            session.flush()
            sample_json = {'apiVersion': 'v1', 'kind': 'FLApp', 'metadata': {}}
            mock_generate_job_run_yaml.return_value = sample_json

            workflow_valid = WorkflowService(session).validate_workflow(workflow)
            self.assertTrue(workflow_valid[0])
            mock_generate_job_run_yaml.side_effect = ValueError
            workflow_valid = WorkflowService(session).validate_workflow(workflow)
            self.assertFalse(workflow_valid[0])

    def test_filter_workflow_state(self):
        with db.session_scope() as session:
            configuring_workflow = Workflow(id=1,
                                            state=WorkflowState.NEW,
                                            target_state=WorkflowState.READY,
                                            transaction_state=TransactionState.READY)
            ready_workflow = Workflow(id=2,
                                      state=WorkflowState.READY,
                                      target_state=WorkflowState.INVALID,
                                      transaction_state=TransactionState.READY)
            completed_workflow = Workflow(id=3, state=WorkflowState.COMPLETED)
            failed_workflow = Workflow(id=4, state=WorkflowState.FAILED)
            running_workflow = Workflow(id=5, state=WorkflowState.RUNNING)
            session.add_all(
                [configuring_workflow, ready_workflow, running_workflow, completed_workflow, failed_workflow])
            session.flush()
            completed_job = Job(id=1, job_type=JobType.RAW_DATA, workflow_id=3, project_id=99, state=JobState.COMPLETED)
            failed_job = Job(id=2, job_type=JobType.RAW_DATA, workflow_id=4, project_id=99, state=JobState.FAILED)
            running_job = Job(id=3, job_type=JobType.RAW_DATA, workflow_id=5, project_id=99, state=JobState.STARTED)
            session.add_all([completed_job, failed_job, running_job])
            session.flush()
            all_workflows = session.query(Workflow)
            self.assertEqual(
                WorkflowService.filter_workflows(all_workflows, ['configuring', 'ready']).all(),
                [configuring_workflow, ready_workflow])
            self.assertEqual(WorkflowService.filter_workflows(all_workflows, ['failed']).all(), [failed_workflow])
            self.assertEqual(WorkflowService.filter_workflows(all_workflows, ['completed']).all(), [completed_workflow])
            self.assertEqual(
                WorkflowService.filter_workflows(all_workflows, ['running', 'completed']).all(),
                [completed_workflow, running_workflow])

    def _get_scheduler_item(self, session) -> SchedulerItem:
        item: SchedulerItem = session.query(SchedulerItem).filter_by(name='workflow_cron_job_1').first()
        return item

    def test_update_cronjob_config(self):
        with db.session_scope() as session:
            # test for collect
            update_cronjob_config(1, '1 2 3 4 5', session)
            session.commit()
            item = self._get_scheduler_item(session)
            self.assertEqual(item.cron_config, '1 2 3 4 5')
            self.assertEqual(item.status, ItemStatus.ON.value)
            item.status = ItemStatus.OFF.value
            session.commit()
        with db.session_scope() as session:
            update_cronjob_config(1, '1 2 3 4 6', session)
            session.commit()
            item = self._get_scheduler_item(session)
            self.assertEqual(item.status, ItemStatus.ON.value)
            self.assertEqual(item.cron_config, '1 2 3 4 6')
        with db.session_scope() as session:
            update_cronjob_config(1, None, session)
            session.commit()
            item = self._get_scheduler_item(session)
            self.assertEqual(item.status, ItemStatus.OFF.value)
            self.assertEqual(item.cron_config, '1 2 3 4 6')


if __name__ == '__main__':
    unittest.main()
