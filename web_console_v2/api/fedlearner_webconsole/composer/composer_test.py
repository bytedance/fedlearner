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

import logging
import sys
import threading
import unittest
from datetime import datetime

from fedlearner_webconsole.composer.composer import Composer, ComposerConfig
from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import ItemStatus, RunnerStatus, SchedulerItem, \
    SchedulerRunner
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, PipelineContextData, RunnerOutput
from testing.composer.common import TestRunner
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.fake_time_patcher import FakeTimePatcher


class ComposerV2Test(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.time_patcher = FakeTimePatcher()
        self.time_patcher.start(datetime(2012, 1, 14, 12, 0, 5))

    runner_fn = {
        ItemType.TASK.value: TestRunner,
    }

    def tearDown(self):
        self.time_patcher.stop()
        super().tearDown()

    def test_multiple_composers(self):
        logging.info('+++++++++++++++++++++++++++ test multiple composers')
        cfg = ComposerConfig(runner_fn=self.runner_fn, name='scheduler for normal items')
        composer1 = Composer(cfg)
        composer2 = Composer(cfg)
        c1 = threading.Thread(target=composer1.run, args=[db.engine])
        c1.start()
        c2 = threading.Thread(target=composer2.run, args=[db.engine])
        c2.start()
        self.time_patcher.interrupt(15)
        composer1.stop()
        composer2.stop()

    def test_normal_items(self):
        logging.info('+++++++++++++++++++++++++++ test normal items')
        cfg = ComposerConfig(runner_fn=self.runner_fn, name='scheduler for normal items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        with db.session_scope() as session:
            name = 'normal items'
            service = ComposerService(session)
            service.collect_v2(name, [(ItemType.TASK, RunnerInput()), (ItemType.TASK, RunnerInput()),
                                      (ItemType.TASK, RunnerInput())])
            session.commit()
        self.time_patcher.interrupt(60)
        with db.session_scope() as session:
            runners = session.query(SchedulerRunner).all()
            self.assertEqual(len(runners), 1, 'Should be only 1 runner')
            self.assertEqual(runners[0].status, RunnerStatus.DONE.value)
            self.assertEqual(
                runners[0].get_context(),
                PipelineContextData(current_runner=2,
                                    outputs={
                                        0: RunnerOutput(),
                                        1: RunnerOutput(),
                                        2: RunnerOutput(),
                                    }))
            # Item should be finished
            item = session.query(SchedulerItem).filter(SchedulerItem.name == 'normal items').first()
            self.assertEqual(item.status, ItemStatus.OFF.value, 'should finish item')
        composer.stop()

    def test_failed_items(self):
        logging.info('+++++++++++++++++++++++++++ test failed items')
        cfg = ComposerConfig(runner_fn=self.runner_fn, name='scheduler for failed items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        with db.session_scope() as session:
            name = 'failed items'
            ComposerService(session).collect_v2(
                name,
                [
                    (ItemType.TASK, RunnerInput()),
                    (ItemType.TASK, RunnerInput()),
                    (ItemType.TASK, RunnerInput()),
                    # Failed one
                    (ItemType.TASK, RunnerInput()),
                    (ItemType.TASK, RunnerInput()),
                ])
            session.commit()
        self.time_patcher.interrupt(60)
        with db.session_scope() as session:
            runners = session.query(SchedulerRunner).all()
            self.assertEqual(len(runners), 1, 'Should be only 1 runner')
            self.assertEqual(runners[0].status, RunnerStatus.FAILED.value)
            self.assertEqual(
                runners[0].get_context(),
                PipelineContextData(current_runner=3,
                                    outputs={
                                        0: RunnerOutput(),
                                        1: RunnerOutput(),
                                        2: RunnerOutput(),
                                        3: RunnerOutput(error_message='index is 3')
                                    }))
            # Item should be finished
            item = session.query(SchedulerItem).filter(SchedulerItem.name == 'failed items').first()
            self.assertEqual(item.status, ItemStatus.OFF.value, 'should finish item')
        composer.stop()

    def test_cron_items(self):
        logging.info('+++++++++++++++++++++++++++ test finishing cron items')
        cfg = ComposerConfig(runner_fn=self.runner_fn, name='finish normal items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        with db.session_scope() as session:
            service = ComposerService(session)
            name = 'cronjob'
            # test invalid cron
            self.assertRaises(ValueError,
                              service.collect_v2,
                              name, [
                                  (ItemType.TASK, RunnerInput()),
                              ],
                              cron_config='invalid cron')

            service.collect_v2(
                name,
                [
                    (ItemType.TASK, RunnerInput()),
                ],
                # Every 10 seconds
                cron_config='* * * * * */10')
            session.commit()
            self.assertEqual(1, len(session.query(SchedulerItem).all()))
        # Interrupts twice since we need two rounds of tick for
        # composer to schedule items in fake world
        self.time_patcher.interrupt(11)
        self.time_patcher.interrupt(11)
        with db.session_scope() as session:
            self.assertEqual(2, len(session.query(SchedulerRunner).all()))
            service = ComposerService(session)
            self.assertEqual(RunnerStatus.DONE.value,
                             service.get_recent_runners(name)[-1].status, 'should finish runner')
            service.finish(name)
            session.commit()
            self.assertEqual(ItemStatus.OFF, service.get_item_status(name), 'should finish item')
        composer.stop()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
