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
from datetime import datetime
from unittest.mock import patch, Mock

from fedlearner_webconsole.composer.models import SchedulerItem, ItemStatus, RunnerStatus, SchedulerRunner
from fedlearner_webconsole.composer.strategy import SingletonStrategy
from fedlearner_webconsole.db import db
from testing.no_web_server_test_case import NoWebServerTestCase


class SingletonStrategyTest(NoWebServerTestCase):

    @patch.object(SchedulerItem, 'need_run')
    def test_should_run_normal_item(self, mock_need_run: Mock):
        with db.session_scope() as session:
            item = SchedulerItem(id=123,
                                 name='test normal item',
                                 status=ItemStatus.ON.value,
                                 created_at=datetime(2021, 9, 1, 10, 10))
            strategy = SingletonStrategy(session)
            mock_need_run.return_value = True
            self.assertTrue(strategy.should_run(item))
            # No need to run
            mock_need_run.return_value = False
            self.assertFalse(strategy.should_run(item))

    @patch.object(SchedulerItem, 'need_run')
    def test_should_run_cron_item(self, mock_need_run: Mock):
        item_id = 123123
        runner_id = 7644
        with db.session_scope() as session:
            item = SchedulerItem(
                id=item_id,
                name='test cron item',
                # Runs every 30 minutes
                cron_config='*/30 * * * *',
                created_at=datetime(2022, 1, 1, 10, 0))
            session.add(item)
            session.commit()
        with db.session_scope() as session:
            strategy = SingletonStrategy(session)
            mock_need_run.return_value = False
            self.assertFalse(strategy.should_run(item))
            mock_need_run.return_value = True
            self.assertTrue(strategy.should_run(item))
            runner = SchedulerRunner(id=runner_id, item_id=item_id, status=RunnerStatus.RUNNING.value)
            session.add(runner)
            session.commit()
        with db.session_scope() as session:
            # Already one running runner, so no new one will be generated.
            item = session.query(SchedulerItem).get(item_id)
            self.assertFalse(strategy.should_run(item))
            runner = session.query(SchedulerRunner).get(runner_id)
            runner.status = RunnerStatus.DONE.value
            session.commit()
        with db.session_scope() as session:
            # All runners are done, so a new one will be there.
            item = session.query(SchedulerItem).get(item_id)
            self.assertTrue(strategy.should_run(item))


if __name__ == '__main__':
    unittest.main()
