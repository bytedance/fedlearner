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

import logging
import unittest
from datetime import datetime

import sys

from fedlearner_webconsole.composer.composer_service import (ComposerService, CronJobService, SchedulerItemService,
                                                             SchedulerRunnerService)
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import RunnerStatus, SchedulerItem, ItemStatus, SchedulerRunner
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, Pipeline, ModelTrainingCronJobInput
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterExpressionKind, SimpleExpression, FilterOp
from testing.no_web_server_test_case import NoWebServerTestCase


class ComposerServiceTest(NoWebServerTestCase):

    def test_collect_v2(self):
        with db.session_scope() as session:
            service = ComposerService(session)
            service.collect_v2('test_item', [(ItemType.TASK, RunnerInput()), (ItemType.TASK, RunnerInput())])
            session.commit()
        with db.session_scope() as session:
            item = session.query(SchedulerItem).filter(SchedulerItem.name == 'test_item').first()
            self.assertEqual(item.status, ItemStatus.ON.value)
            self.assertIsNone(item.cron_config)
            self.assertEqual(
                item.get_pipeline(),
                Pipeline(
                    version=2,
                    name='test_item',
                    queue=[RunnerInput(runner_type=ItemType.TASK.value),
                           RunnerInput(runner_type=ItemType.TASK.value)]))

    def test_collect_v2_duplication(self):
        with db.session_scope() as session:
            service = ComposerService(session)
            service.collect_v2('test_item', [(ItemType.TASK, RunnerInput())])
            session.commit()
            service.collect_v2('test_item', [(ItemType.TASK, RunnerInput())])
            session.commit()
        with db.session_scope() as session:
            items = session.query(SchedulerItem).filter(SchedulerItem.name == 'test_item').all()
            self.assertEqual(len(items), 1)

    def test_collect_v2_cron(self):
        with db.session_scope() as session:
            service = ComposerService(session)
            service.collect_v2('test_cron_item', [
                (ItemType.TASK, RunnerInput()),
            ], '* * * * * */10')
            session.commit()
        with db.session_scope() as session:
            item = session.query(SchedulerItem).filter(SchedulerItem.name == 'test_cron_item').first()
            self.assertEqual(item.status, ItemStatus.ON.value)
            self.assertEqual(item.cron_config, '* * * * * */10')
            self.assertEqual(
                item.get_pipeline(),
                Pipeline(version=2, name='test_cron_item', queue=[RunnerInput(runner_type=ItemType.TASK.value)]))

    def test_finish(self):
        with db.session_scope() as session:
            item = SchedulerItem(id=100, name='fake_item', status=ItemStatus.ON.value)
            runner_1 = SchedulerRunner(id=100, item_id=100, status=RunnerStatus.RUNNING.value)
            runner_2 = SchedulerRunner(id=101, item_id=100, status=RunnerStatus.DONE.value)
            runner_3 = SchedulerRunner(id=102, item_id=100, status=RunnerStatus.FAILED.value)
            runner_4 = SchedulerRunner(id=103, item_id=100, status=RunnerStatus.INIT.value)
            session.add(item)
            session.add(runner_1)
            session.add(runner_2)
            session.add(runner_3)
            session.add(runner_4)
            session.commit()

        with db.session_scope() as session:
            service = ComposerService(session)
            service.finish(name='fake_item')
            session.commit()

        with db.session_scope() as session:
            item = session.query(SchedulerItem).get(100)
            runner_1 = session.query(SchedulerRunner).get(100)
            runner_2 = session.query(SchedulerRunner).get(101)
            runner_3 = session.query(SchedulerRunner).get(102)
            runner_4 = session.query(SchedulerRunner).get(103)

            self.assertEqual(item.status, ItemStatus.OFF.value)
            self.assertIsNone(runner_1)
            self.assertEqual(runner_2.status, RunnerStatus.DONE.value)
            self.assertEqual(runner_3.status, RunnerStatus.FAILED.value)
            self.assertIsNone(runner_4)

    def test_get_recent_runners(self):
        with db.session_scope() as session:
            item = SchedulerItem(id=100, name='fake_item', status=ItemStatus.ON.value)
            runner_1 = SchedulerRunner(id=100,
                                       item_id=100,
                                       status=RunnerStatus.RUNNING.value,
                                       created_at=datetime(2012, 1, 14, 12, 0, 6))
            runner_2 = SchedulerRunner(id=101,
                                       item_id=100,
                                       status=RunnerStatus.DONE.value,
                                       created_at=datetime(2012, 1, 14, 12, 0, 7))
            runner_3 = SchedulerRunner(id=102,
                                       item_id=100,
                                       status=RunnerStatus.FAILED.value,
                                       created_at=datetime(2012, 1, 14, 12, 0, 8))
            runner_4 = SchedulerRunner(id=103,
                                       item_id=100,
                                       status=RunnerStatus.INIT.value,
                                       created_at=datetime(2012, 1, 14, 12, 0, 9))
            session.add_all([item, runner_1, runner_2, runner_3, runner_4])
            session.commit()

        with db.session_scope() as session:
            expect_runners = [runner_4, runner_3, runner_2, runner_1]
            runners = ComposerService(session).get_recent_runners(name='fake_item', count=10)
            self.assertEqual(len(runners), 4)
            for i in range(4):
                self.assertEqual(runners[i].id, expect_runners[i].id)
                self.assertEqual(runners[i].status, expect_runners[i].status)
                self.assertEqual(runners[i].item_id, 100)

            runners = ComposerService(session).get_recent_runners(name='fake_item', count=1)
            self.assertEqual(len(runners), 1)
            self.assertEqual(runners[0].id, expect_runners[0].id)
            self.assertEqual(runners[0].status, expect_runners[0].status)
            self.assertEqual(runners[0].item_id, 100)

    def test_patch_item_attr(self):
        test_item_name = 'test'
        with db.session_scope() as session:
            scheduler_item = SchedulerItem(name=test_item_name, cron_config='* */1 * * *')
            session.add(scheduler_item)
            session.commit()
        with db.session_scope() as session:
            service = ComposerService(session)
            service.patch_item_attr(name=test_item_name, key='cron_config', value='*/20 * * * *')
            session.commit()
        with db.session_scope() as session:
            item = session.query(SchedulerItem).filter(SchedulerItem.name == test_item_name).one()
            self.assertEqual(item.cron_config, '*/20 * * * *')
        with self.assertRaises(ValueError):
            with db.session_scope() as session:
                ComposerService(session).patch_item_attr(name=test_item_name,
                                                         key='create_at',
                                                         value='2021-04-01 00:00:00')
                session.commit()


class CronJobServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            item = SchedulerItem(id=1,
                                 name='model_training_cronjob_1',
                                 cron_config='*/10 * * * *',
                                 status=ItemStatus.ON.value)
            session.add(item)
            session.commit()

    def test_start_cronjob(self):
        with db.session_scope() as session:
            items = [(ItemType.MODEL_TRAINING_CRON_JOB,
                      RunnerInput(model_training_cron_job_input=ModelTrainingCronJobInput(group_id=1)))]
            CronJobService(session).start_cronjob('model_training_cronjob_1', items, '*/20 * * * *')
            CronJobService(session).start_cronjob('model_training_cronjob_2', items, '*/20 * * * *')
            session.commit()
        with db.session_scope() as session:
            item_1 = session.query(SchedulerItem).get(1)
            self.assertEqual(item_1.cron_config, '*/20 * * * *')
            item_2 = session.query(SchedulerItem).filter_by(name='model_training_cronjob_2').first()
            self.assertEqual(item_2.cron_config, '*/20 * * * *')

    def test_stop_cronjob(self):
        with db.session_scope() as session:
            CronJobService(session).stop_cronjob('model_training_cronjob_1')
            session.commit()
        with db.session_scope() as session:
            item = session.query(SchedulerItem).get(1)
            self.assertEqual(item.status, ItemStatus.OFF.value)


class SchedulerItemServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        scheduler_item_off = SchedulerItem(id=5,
                                           name='test_item_off',
                                           status=ItemStatus.OFF.value,
                                           created_at=datetime(2022, 1, 1, 12, 0, 0),
                                           updated_at=datetime(2022, 1, 1, 12, 0, 0))
        scheduler_item_on = SchedulerItem(id=6,
                                          name='test_item_on',
                                          status=ItemStatus.ON.value,
                                          created_at=datetime(2022, 1, 1, 12, 0, 0),
                                          updated_at=datetime(2022, 1, 1, 12, 0, 0))
        scheduler_item_on_cron = SchedulerItem(id=7,
                                               name='test_item_on_cron',
                                               cron_config='*/20 * * * *',
                                               status=ItemStatus.ON.value,
                                               created_at=datetime(2022, 1, 1, 12, 0, 0),
                                               updated_at=datetime(2022, 1, 1, 12, 0, 0))

        with db.session_scope() as session:
            session.add(scheduler_item_on)
            session.add(scheduler_item_off)
            session.add(scheduler_item_on_cron)
            session.commit()

    def test_get_scheduler_items(self):
        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='is_cron',
                                          op=FilterOp.EQUAL,
                                          bool_value=1,
                                      ))
        with db.session_scope() as session:
            service = SchedulerItemService(session)
            paginations = service.get_scheduler_items(filter_exp=filter_exp, page=1, page_size=7)
            item_ids = [item.id for item in paginations.get_items()]
            self.assertEqual(item_ids, [7])


class SchedulerRunnerServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        scheduler_item_on = SchedulerItem(id=100,
                                          name='test_item_on',
                                          status=ItemStatus.ON.value,
                                          created_at=datetime(2022, 1, 1, 12, 0, 0),
                                          updated_at=datetime(2022, 1, 1, 12, 0, 0))
        self.default_scheduler_item = scheduler_item_on
        runner_init = SchedulerRunner(id=0, item_id=100, status=RunnerStatus.INIT.value)
        runner_running_1 = SchedulerRunner(id=1, item_id=100, status=RunnerStatus.RUNNING.value)
        runner_running_2 = SchedulerRunner(id=2, item_id=100, status=RunnerStatus.RUNNING.value)

        with db.session_scope() as session:
            session.add(scheduler_item_on)
            session.add(runner_init)
            session.add(runner_running_1)
            session.add(runner_running_2)
            session.commit()

    def test_get_scheduler_runners(self):
        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='status',
                                          op=FilterOp.EQUAL,
                                          string_value='INIT',
                                      ))
        with db.session_scope() as session:
            service = SchedulerRunnerService(session)
            paginations = service.get_scheduler_runners(filter_exp=filter_exp, page=1, page_size=7)
            item_ids = [item.id for item in paginations.get_items()]
            self.assertEqual(item_ids, [0])


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
