# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

from time import sleep
from sqlalchemy import and_

from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.workflow.cronjob import WorkflowCronJob, WorkflowCronJobItem
from fedlearner_webconsole.composer.models import Context, RunnerStatus, SchedulerItem, SchedulerRunner
from fedlearner_webconsole.composer.composer import ComposerConfig
from fedlearner_webconsole.composer.interface import ItemType


class CronJobTest(BaseTestCase):
    """Disable for now, hacking!!!!
    
        Hopefully it will enabled again!
    """
    def setUp(self):
        super(CronJobTest, self).setUp()
        self.test_id = 8848
        workflow = Workflow(id=self.test_id, state=WorkflowState.RUNNING)
        db.session.add(workflow)
        db.session.commit()

    @unittest.skip('waiting for refactor of transaction state')
    def test_cronjob_alone(self):
        cronjob = WorkflowCronJob(task_id=self.test_id)
        context = Context(data={}, internal={}, db_engine=db.engine)
        cronjob.start(context)
        status, output = cronjob.result(context)
        self.assertEqual(status, RunnerStatus.DONE)
        self.assertTrue(output['msg'] is not None)

    @unittest.skip('waiting for refactor of transaction state')
    def test_cronjob_with_composer(self):
        config = ComposerConfig(
            runner_fn={ItemType.WORKFLOW_CRON_JOB.value: WorkflowCronJob},
            name='test_cronjob')
        with self.composer_scope(config=config) as composer:
            item_name = f'workflow_cronjob_{self.test_id}'
            composer.collect(name=item_name,
                             items=[WorkflowCronJobItem(self.test_id)],
                             metadata={},
                             interval=10)
            sleep(20)
            runners = SchedulerRunner.query.filter(
                and_(SchedulerRunner.item_id == SchedulerItem.id,
                     SchedulerItem.name == item_name)).all()
            self.assertEqual(len(runners), 2)


if __name__ == '__main__':
    unittest.main()
