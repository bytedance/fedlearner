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
from http import HTTPStatus

from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.models import (SchedulerItem, SchedulerRunner, ItemStatus, RunnerStatus)


class DebugSchedulerApiTest(BaseTestCase):

    _ITEM_ON_ID = 123
    _PRESET_SCHEDULER_ITEM = [
        'test_item_off',
        'test_item_on',
        'workflow_scheduler_v2',
        'job_scheduler_v2',
        'cleanup_cron_job',
        'dataset_short_period_scheduler',
        'dataset_long_period_scheduler',
        'project_scheduler_v2',
        'tee_create_runner',
        'tee_resource_check_runner',
        'model_job_scheduler_runner',
        'model_job_group_scheduler_runner',
        'model_job_group_long_period_scheduler_runner',
    ]

    def setUp(self):
        super().setUp()
        scheduler_item_on = SchedulerItem(id=self._ITEM_ON_ID, name='test_item_on', status=ItemStatus.ON.value)
        scheduler_item_off = SchedulerItem(name='test_item_off', status=ItemStatus.OFF.value)
        with db.session_scope() as session:
            session.add_all([scheduler_item_on, scheduler_item_off])
            session.commit()
        scheduler_runner_init = SchedulerRunner(id=0, item_id=self._ITEM_ON_ID, status=RunnerStatus.INIT.value)
        scheduler_runner_running_1 = SchedulerRunner(id=1, item_id=self._ITEM_ON_ID, status=RunnerStatus.RUNNING.value)
        scheduler_runner_running_2 = SchedulerRunner(id=2, item_id=self._ITEM_ON_ID, status=RunnerStatus.RUNNING.value)

        with db.session_scope() as session:
            session.add_all([scheduler_runner_init, scheduler_runner_running_1, scheduler_runner_running_2])
            session.commit()

    def test_get_scheduler_item(self):
        # test get all scheduler item
        data = self.get_response_data(self.get_helper('/api/v2/debug/scheduler_items'))
        # there exists a preset scheduler item
        self.assertCountEqual([d['name'] for d in data], self._PRESET_SCHEDULER_ITEM)
        # test get scheduler item with status
        data = self.get_response_data(self.get_helper('/api/v2/debug/scheduler_items?status=0'))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'test_item_off')
        # test get recent scheduler runners
        data = self.get_response_data(self.get_helper(f'/api/v2/debug/scheduler_items?id={self._ITEM_ON_ID}'))
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['status'], RunnerStatus.INIT.value)

    def test_get_scheduler_runner(self):
        # test get running runners
        response = self.get_helper('/api/v2/debug/scheduler_runners?status=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['id'], 1)


if __name__ == '__main__':
    unittest.main()
