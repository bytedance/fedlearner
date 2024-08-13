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
import urllib.parse
from http import HTTPStatus
from datetime import datetime
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.models import SchedulerItem, SchedulerRunner, ItemStatus, RunnerStatus
import json
from fedlearner_webconsole.utils.proto import to_json
from fedlearner_webconsole.proto import composer_pb2


class SchedulerItemsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        # ids from 1001 to 1004 work as cron_job with status "ON"
        scheduler_item_off = SchedulerItem(id=1001,
                                           name='test_item_off',
                                           status=ItemStatus.OFF.value,
                                           created_at=datetime(2022, 1, 1, 12, 0, 0),
                                           updated_at=datetime(2022, 1, 1, 12, 0, 0))
        scheduler_item_on = SchedulerItem(id=1002,
                                          name='test_item_on',
                                          status=ItemStatus.ON.value,
                                          created_at=datetime(2022, 1, 1, 12, 0, 0),
                                          updated_at=datetime(2022, 1, 1, 12, 0, 0))
        scheduler_item_on_cron = SchedulerItem(id=1003,
                                               name='test_item_on_cron',
                                               cron_config='*/20 * * * *',
                                               status=ItemStatus.ON.value,
                                               created_at=datetime(2022, 1, 1, 12, 0, 0),
                                               updated_at=datetime(2022, 1, 1, 12, 0, 0))
        scheduler_item_off_cron = SchedulerItem(id=1004,
                                                name='test_item_off_cron',
                                                cron_config='*/20 * * * *',
                                                status=ItemStatus.OFF.value,
                                                created_at=datetime(2022, 1, 1, 12, 0, 0),
                                                updated_at=datetime(2022, 1, 1, 12, 0, 0))
        scheduler_item_for_id_test = SchedulerItem(id=201,
                                                   name='scheduler_item_for_id_test',
                                                   cron_config='*/20 * * * *',
                                                   status=ItemStatus.ON.value,
                                                   created_at=datetime(2022, 1, 1, 12, 0, 0),
                                                   updated_at=datetime(2022, 1, 1, 12, 0, 0))

        with db.session_scope() as session:
            session.add(scheduler_item_on)
            session.add(scheduler_item_off)
            session.add(scheduler_item_on_cron)
            session.add(scheduler_item_off_cron)
            session.add(scheduler_item_for_id_test)
            session.commit()
        self.signin_as_admin()

    def test_get_with_pagination(self):
        response = self.get_helper('/api/v2/scheduler_items?page=1&page_size=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 1004)

    def test_get_with_invalid_filter(self):
        response = self.get_helper('/api/v2/scheduler_items?filter=invalid')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_with_id_filter(self):
        filter_exp = urllib.parse.quote('(id=201)')
        response = self.get_helper(f'/api/v2/scheduler_items?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'scheduler_item_for_id_test')

    def test_get_with_three_filter(self):
        filter_exp = urllib.parse.quote('(and(is_cron=true)(status="OFF")(name~="item_off_cron"))')
        response = self.get_helper(f'/api/v2/scheduler_items?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['status'], ItemStatus.OFF.name)
        self.assertNotEqual(data[0]['cron_config'], '')

    def test_get_with_single_filter(self):
        filter_exp = urllib.parse.quote('(status="OFF")')
        response = self.get_helper(f'/api/v2/scheduler_items?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['status'], ItemStatus.OFF.name)


class SchedulerItemApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        scheduler_item_on = SchedulerItem(id=100,
                                          name='test_item_on',
                                          status=ItemStatus.ON.value,
                                          created_at=datetime(2022, 1, 1, 12, 0, 0),
                                          updated_at=datetime(2022, 1, 1, 12, 0, 0))
        self.default_scheduler_item = scheduler_item_on
        self.default_context = json.dumps({'outputs': {'0': {'job_scheduler_output': {}}}})
        self.default_output = to_json(composer_pb2.RunnerOutput(error_message='error1'))
        runner_init = SchedulerRunner(id=0,
                                      item_id=100,
                                      status=RunnerStatus.INIT.value,
                                      context=self.default_context,
                                      output=self.default_output)
        runner_running_1 = SchedulerRunner(id=1,
                                           item_id=100,
                                           status=RunnerStatus.RUNNING.value,
                                           context=self.default_context,
                                           output=self.default_output)
        runner_running_2 = SchedulerRunner(id=2,
                                           item_id=100,
                                           status=RunnerStatus.RUNNING.value,
                                           context=self.default_context,
                                           output=self.default_output)

        with db.session_scope() as session:
            session.add(scheduler_item_on)
            session.add(runner_init)
            session.add(runner_running_1)
            session.add(runner_running_2)
            session.commit()
        self.signin_as_admin()

    def test_get_runners_without_pagination(self):
        response = self.get_helper(f'/api/v2/scheduler_items/{self.default_scheduler_item.id}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 3)

    def test_get_with_pagination(self):
        response = self.get_helper(f'/api/v2/scheduler_items/{self.default_scheduler_item.id}?page=1&page_size=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)

    def test_change_scheduleritem_status(self):
        get_response = self.patch_helper(f'/api/v2/scheduler_items/{self.default_scheduler_item.id}',
                                         data={'status': 'OFF'})
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            dataset = session.query(SchedulerItem).get(self.default_scheduler_item.id)
            self.assertEqual(dataset.status, ItemStatus.OFF.value)

    def test_change_scheduleritem_status_with_invalid_argument(self):
        get_response = self.patch_helper(f'/api/v2/scheduler_items/{self.default_scheduler_item.id}',
                                         data={'status': 'RUNNING'})
        self.assertEqual(get_response.status_code, HTTPStatus.BAD_REQUEST)
        with db.session_scope() as session:
            dataset = session.query(SchedulerItem).get(self.default_scheduler_item.id)
            self.assertEqual(dataset.status, ItemStatus.ON.value)


class SchedulerRunnersApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        scheduler_item_on = SchedulerItem(id=100,
                                          name='test_item_on',
                                          status=ItemStatus.ON.value,
                                          created_at=datetime(2022, 1, 1, 12, 0, 0),
                                          updated_at=datetime(2022, 1, 1, 12, 0, 0))
        self.default_scheduler_item = scheduler_item_on
        self.default_context = json.dumps({'outputs': {'0': {'job_scheduler_output': {}}}})
        self.default_output = to_json(composer_pb2.RunnerOutput(error_message='error1'))
        runner_init = SchedulerRunner(id=0,
                                      item_id=100,
                                      status=RunnerStatus.INIT.value,
                                      context=self.default_context,
                                      output=self.default_output)
        runner_running = SchedulerRunner(id=1,
                                         item_id=100,
                                         status=RunnerStatus.RUNNING.value,
                                         context=self.default_context)
        runner_running_2 = SchedulerRunner(id=2,
                                           item_id=100,
                                           status=RunnerStatus.RUNNING.value,
                                           context=self.default_context)
        runner_done = SchedulerRunner(id=3, item_id=100, status=RunnerStatus.DONE.value)

        with db.session_scope() as session:
            session.add(scheduler_item_on)
            session.add(runner_init)
            session.add(runner_running)
            session.add(runner_running_2)
            session.add(runner_done)
            session.commit()
        self.signin_as_admin()

    def test_get_without_filter_and_pagination(self):
        response = self.get_helper('/api/v2/scheduler_runners')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 4)

    def test_get_with_pagination(self):
        response = self.get_helper('/api/v2/scheduler_runners?page=1&page_size=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)

    def test_get_with_invalid_filter(self):
        response = self.get_helper('/api/v2/scheduler_runners?filter=invalid')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_with_filter(self):
        filter_exp = urllib.parse.quote('(status="RUNNING")')
        response = self.get_helper(f'/api/v2/scheduler_runners?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['status'], RunnerStatus.RUNNING.name)
        self.assertEqual(data[1]['status'], RunnerStatus.RUNNING.name)


if __name__ == '__main__':
    unittest.main()
