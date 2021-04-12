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
import sys
import threading
import time
import unittest
from typing import Tuple

from testing.common import BaseTestCase

from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.composer import Composer, ComposerConfig
from fedlearner_webconsole.composer.models import RunnerStatus, SchedulerItem, \
    SchedulerRunner, Context
from fedlearner_webconsole.composer.interface import IItem, IRunner, ItemType


class Task(IItem):
    def __init__(self, task_id: int):
        self.id = task_id

    def type(self) -> ItemType:
        return ItemType.TASK

    def get_id(self) -> int:
        return self.id


def raise_(ex):
    raise ex


def sleep_and_log(id: int, sec: int):
    time.sleep(sec)
    logging.info(f'id-{id}, sleep {sec}')


RunnerCases = [
    # normal: 1, 2, 3
    {
        'id': 1,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(1, 1) or (RunnerStatus.DONE, {})),
        'stop': (lambda _: None),
    },
    {
        'id': 2,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(2, 1) or (RunnerStatus.DONE, {})),
        'stop': (lambda _: None),
    },
    {
        'id': 3,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(3, 1) or (RunnerStatus.DONE, {})),
        'stop': (lambda _: None),
    },
    # failed: 4, 5, 6
    {
        'id': 4,
        'start': (lambda _: sleep_and_log(4, 5) and False),
        'result': (lambda _: (RunnerStatus.FAILED, {})),
        'stop': (lambda _: _),
    },
    {
        'id': 5,
        'start': (lambda _: raise_(TimeoutError)),
        'result': (lambda _: (RunnerStatus.FAILED, {})),
        'stop': (lambda _: _),
    },
    {
        'id': 6,
        'start': (lambda _: sleep_and_log(6, 10) and False),
        'result': (lambda _: (RunnerStatus.FAILED, {})),
        'stop': (lambda _: _),
    },
    # busy: 7, 8, 9
    {
        'id': 7,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(7, 15) or (RunnerStatus.DONE, {})),
        'stop': (lambda _: _),
    },
    {
        'id': 8,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(8, 15) or (RunnerStatus.DONE, {})),
        'stop': (lambda _: _),
    },
    {
        'id': 9,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(9, 15) or (RunnerStatus.DONE, {})),
        'stop': (lambda _: _),
    },
]


class TaskRunner(IRunner):
    def __init__(self, task_id: int):
        self.task_id = task_id

    def start(self, context: Context):
        logging.info(
            f"[mock_task_runner] {self.task_id} started, ctx: {context}")
        RunnerCases[self.task_id - 1]['start'](context)

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        result = RunnerCases[self.task_id - 1]['result'](context)
        logging.info(f"[mock_task_runner] {self.task_id} done result {result}")
        return result

    def stop(self, context: Context):
        logging.info(
            f"[mock_task_runner] {self.task_id} stopped, ctx: {context}")
        RunnerCases[self.task_id - 1]['stop'](context)

    def timeout(self) -> int:
        return 60


class ComposerTest(BaseTestCase):
    runner_fn = {
        ItemType.TASK.value: TaskRunner,
    }

    class Config(BaseTestCase.Config):
        STORAGE_ROOT = '/tmp'
        START_SCHEDULER = False
        START_GRPC_SERVER = False

    def setUp(self):
        super().setUp()

    def test_normal_items(self):
        logging.info('+++++++++++++++++++++++++++ test normal items')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='scheduler for normal items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        normal_items = [Task(1), Task(2), Task(3)]
        composer.collect('normal items', normal_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect items')
        # test unique item name
        composer.collect('normal items', normal_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect items')
        time.sleep(20)
        self.assertEqual(1, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.DONE.value,
                         db.session.query(SchedulerRunner).first().status,
                         'should finish it')
        composer.stop()

    def test_failed_items(self):
        logging.info('+++++++++++++++++++++++++++ test failed items')
        cfg = ComposerConfig(runner_fn=self.runner_fn,
                             name='scheduler for failed items')
        composer = Composer(config=cfg)
        composer.run(db_engine=db.engine)
        failed_items = [Task(4), Task(5), Task(6)]
        composer.collect('failed items', failed_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect failed items')
        time.sleep(30)
        self.assertEqual(1, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.FAILED.value,
                         db.session.query(SchedulerRunner).first().status,
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
        composer.collect('busy items', busy_items, {})
        self.assertEqual(1, len(db.session.query(SchedulerItem).all()),
                         'incorrect busy items')
        time.sleep(20)
        self.assertEqual(1, len(db.session.query(SchedulerRunner).all()),
                         'incorrect runners')
        self.assertEqual(RunnerStatus.RUNNING.value,
                         db.session.query(SchedulerRunner).first().status,
                         'should finish it')
        composer.stop()
        time.sleep(5)

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
        time.sleep(20)
        composer1.stop()
        composer2.stop()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
