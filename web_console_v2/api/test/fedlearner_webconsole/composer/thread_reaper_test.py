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
import time
import unittest
from typing import Tuple

from testing.common import BaseTestCase
from fedlearner_webconsole.composer.models import Context, RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.interface import IRunner
from fedlearner_webconsole.composer.thread_reaper import ThreadReaper


class TaskRunner(IRunner):
    def __init__(self, task_id: int):
        self.task_id = task_id

    def start(self, context: Context):
        logging.info(
            f"[mock_task_runner] {self.task_id} started, ctx: {context}")
        time.sleep(5)

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        time.sleep(3)
        return RunnerStatus.DONE, {}


class ThreadReaperTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        STORAGE_ROOT = '/tmp'
        START_SCHEDULER = False
        START_GRPC_SERVER = False

    def setUp(self):
        super().setUp()

    def test_thread_reaper(self):
        tr = ThreadReaper(worker_num=1)

        runner = TaskRunner(1)
        tr.enqueue('1', runner,
                   Context(data={}, internal={}, db_engine=db.engine))
        self.assertEqual(True, tr.is_full(), 'should be full')
        ok = tr.enqueue('2', runner,
                        Context(data={}, internal={}, db_engine=db.engine))
        self.assertEqual(False, ok, 'should not be enqueued')
        time.sleep(10)
        self.assertEqual(False, tr.is_full(), 'should not be full')
        ok = tr.enqueue('3', runner,
                        Context(data={}, internal={}, db_engine=db.engine))
        self.assertEqual(True, ok, 'should be enqueued')
        tr.stop(wait=True)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
