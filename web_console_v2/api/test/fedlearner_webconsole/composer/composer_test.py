# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import pprint
import sys
import threading
import time
import unittest

from testing.common import BaseTestCase
from test.fedlearner_webconsole.composer.common import TaskRunner, Task, InputDirTaskRunner

from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.composer import Composer, ComposerConfig
from fedlearner_webconsole.composer.models import ItemStatus, RunnerStatus, SchedulerItem, \
    SchedulerRunner
from fedlearner_webconsole.composer.interface import ItemType


class ComposerTest(BaseTestCase):
    runner_fn = {
        ItemType.TASK.value: TaskRunner,
    }

    class Config(BaseTestCase.Config):
        STORAGE_ROOT = '/tmp'
        START_SCHEDULER = False
        START_GRPC_SERVER = False

    def test_normal_items(self):
        logging.info('+++++++++++++++++++++++++++ test normal items')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='scheduler for normal items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        normal_items = [Task(1), Task(2), Task(3)]
        name = 'normal items'
        composer.collect(name, normal_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect items')
        # test unique item name
        composer.collect(name, normal_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect items')
        time.sleep(20)
        self.assertEqual(1, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.DONE.value,
                         composer.get_recent_runners(name)[-1].status,
                         'should finish runner')
        # finish item
        composer.finish(name)
        self.assertEqual(ItemStatus.OFF, composer.get_item_status(name),
                         'should finish item')
        composer.stop()

    def test_failed_items(self):
        logging.info('+++++++++++++++++++++++++++ test failed items')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='scheduler for failed items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        failed_items = [Task(4), Task(5), Task(6)]
        name = 'failed items'
        composer.collect(name, failed_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect failed items')
        time.sleep(30)
        self.assertEqual(1, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.FAILED.value,
                         composer.get_recent_runners(name)[-1].status,
                         'should finish it')
        composer.stop()

    def test_busy_items(self):
        logging.info('+++++++++++++++++++++++++++ test busy items')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='scheduler for busy items',
                             worker_num=1)
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        busy_items = [Task(7), Task(8), Task(9)]
        name = 'busy items'
        composer.collect(name, busy_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect busy items')
        time.sleep(20)
        self.assertEqual(1, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.RUNNING.value,
                         composer.get_recent_runners(name)[-1].status,
                         'should finish it')
        composer.stop()
        time.sleep(5)

    def test_interval_items(self):
        logging.info(
            '+++++++++++++++++++++++++++ test finishing interval items')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='finish normal items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        name = 'cronjob'
        # test invalid interval
        self.assertRaises(ValueError,
                          composer.collect,
                          name, [Task(1)], {},
                          interval=9)

        composer.collect(name, [Task(1)], {}, interval=10)
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect items')
        time.sleep(20)
        self.assertEqual(2, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.DONE.value,
                         composer.get_recent_runners(name)[-1].status,
                         'should finish runner')
        composer.finish(name)
        self.assertEqual(ItemStatus.OFF, composer.get_item_status(name),
                         'should finish item')
        composer.stop()

    def test_multiple_composers(self):
        logging.info('+++++++++++++++++++++++++++ test multiple composers')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='scheduler for normal items')
        composer1 = Composer(cfg)
        composer2 = Composer(cfg)
        c1 = threading.Thread(target=composer1.run, args=[db.engine])
        c1.start()
        c2 = threading.Thread(target=composer2.run, args=[db.engine])
        c2.start()
        time.sleep(15)
        composer1.stop()
        composer2.stop()

    def test_runner_cache(self):
        logging.info('+++++++++++++++++++++++++++ test runner cache')
        composer = Composer(
            config=ComposerConfig(runner_fn={
                ItemType.TASK.value: InputDirTaskRunner,
            },
                                  name='runner cache'))
        composer.run(db_engine=db.engine)
        composer.collect('item1', [Task(1)], {
            1: {
                'input_dir': 'item1_input_dir',
            },
        })
        composer.collect('item2', [Task(1)], {
            1: {
                'input_dir': 'item2_input_dir',
            },
        })
        time.sleep(15)
        self.assertEqual(2, len(db.session.query(SchedulerItem).all()),
                         'incorrect items')
        self.assertEqual(2, len(composer.runner_cache.data),
                         'should be equal runner number')
        pprint.pprint(composer.runner_cache)
        self.assertEqual(
            'item1_input_dir',
            composer.runner_cache.find_runner(1, 'task_1').input_dir,
            'should be item1_input_dir')
        self.assertEqual(
            'item2_input_dir',
            composer.runner_cache.find_runner(2, 'task_1').input_dir,
            'should be item2_input_dir')
        # test delete cache item
        composer.collect(
            'item3', [Task(2), Task(3)], {
                2: {
                    'input_dir': 'item3_input_dir_2',
                },
                3: {
                    'input_dir': 'item3_input_dir_3',
                }
            })
        time.sleep(15)
        self.assertEqual(2, len(composer.runner_cache.data),
                         'should be equal runner number')
        composer.stop()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
