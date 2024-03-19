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
from datetime import datetime
from unittest.mock import patch, Mock

from sqlalchemy import and_

from fedlearner_webconsole.composer.composer import ComposerConfig, Composer
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import RunnerStatus, SchedulerItem, SchedulerRunner
from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, WorkflowCronJobInput
from fedlearner_webconsole.workflow.cronjob import WorkflowCronJob
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.fake_time_patcher import FakeTimePatcher


class CronJobTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.time_patcher = FakeTimePatcher()
        self.time_patcher.start(datetime(2012, 1, 14, 12, 0, 5))

        self.test_id = 8848
        workflow = Workflow(id=self.test_id, state=WorkflowState.RUNNING)
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()

    def tearDown(self):
        self.time_patcher.stop()

        super().tearDown()

    def test_run_skip_running_workflow(self):
        workflow_id = 123
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.RUNNING)
            session.add(workflow)
            session.commit()

        context = RunnerContext(0, RunnerInput(workflow_cron_job_input=WorkflowCronJobInput(workflow_id=workflow_id)))
        runner = WorkflowCronJob()
        status, output = runner.run(context)
        self.assertEqual(status, RunnerStatus.DONE)
        self.assertEqual(output.workflow_cron_job_output.message, 'Skip starting workflow, state is RUNNING')

    @patch('fedlearner_webconsole.workflow.cronjob.start_workflow')
    def test_run_ready_workflow(self, mock_start_workflow: Mock):
        workflow_id = 234
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.READY)
            session.add(workflow)
            session.commit()

        context = RunnerContext(0, RunnerInput(workflow_cron_job_input=WorkflowCronJobInput(workflow_id=workflow_id)))
        runner = WorkflowCronJob()
        status, output = runner.run(context)
        self.assertEqual(status, RunnerStatus.DONE)
        self.assertEqual(output.workflow_cron_job_output.message, 'Restarted workflow')
        mock_start_workflow.assert_called_once_with(workflow_id)

    def test_cronjob_with_composer(self):
        item_name = f'workflow_cronjob_{self.test_id}'
        config = ComposerConfig(runner_fn={ItemType.WORKFLOW_CRON_JOB.value: WorkflowCronJob}, name='test_cronjob')
        composer = Composer(config=config)
        with db.session_scope() as session:
            service = ComposerService(session)
            service.collect_v2(name=item_name,
                               items=[
                                   (ItemType.WORKFLOW_CRON_JOB,
                                    RunnerInput(workflow_cron_job_input=WorkflowCronJobInput(workflow_id=self.test_id)))
                               ],
                               cron_config='* * * * * */10')
            session.commit()
        composer.run(db_engine=db.engine)
        # Interrupts twice since we need two rounds of tick for
        # composer to schedule items in fake world
        self.time_patcher.interrupt(10)
        self.time_patcher.interrupt(10)
        with db.session_scope() as session:
            runners = session.query(SchedulerRunner).filter(
                and_(SchedulerRunner.item_id == SchedulerItem.id, SchedulerItem.name == item_name)).all()
            self.assertEqual(len(runners), 2)
        composer.stop()


if __name__ == '__main__':
    unittest.main()
