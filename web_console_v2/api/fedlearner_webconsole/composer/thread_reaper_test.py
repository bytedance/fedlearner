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
from concurrent.futures import Future

import sys
import unittest

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.thread_reaper import ThreadReaper
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput
from testing.composer.common import TestRunner

from testing.no_web_server_test_case import NoWebServerTestCase
from testing.fake_time_patcher import FakeTimePatcher


class ThreadReaperTest(NoWebServerTestCase):

    class Config(NoWebServerTestCase.Config):
        STORAGE_ROOT = '/tmp'
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        self.fake_time_patcher = FakeTimePatcher()
        self.fake_time_patcher.start()

    def tearDown(self):
        self.fake_time_patcher.stop()
        return super().tearDown()

    def test_submit(self):
        thread_reaper = ThreadReaper(worker_num=2)
        runner = TestRunner()
        submitted = thread_reaper.submit(
            runner_id=123,
            fn=runner,
            context=RunnerContext(0, RunnerInput()),
        )
        self.assertTrue(submitted)
        self.assertTrue(thread_reaper.is_running(123))
        self.assertFalse(thread_reaper.is_full())
        # Submit again
        submitted = thread_reaper.submit(
            runner_id=123,
            fn=runner,
            context=RunnerContext(0, RunnerInput()),
        )
        self.assertFalse(submitted)
        self.assertFalse(thread_reaper.is_full())
        submitted = thread_reaper.submit(
            runner_id=3333,
            fn=runner,
            context=RunnerContext(1, RunnerInput()),
        )
        self.assertTrue(submitted)
        self.assertTrue(thread_reaper.is_full())
        self.fake_time_patcher.interrupt(5)
        self.assertFalse(thread_reaper.is_running(123))
        self.assertFalse(thread_reaper.is_full())
        thread_reaper.stop(wait=True)

    def test_submit_with_exception(self):
        thread_reaper = ThreadReaper(worker_num=1)
        error = None
        runner_id = None

        def done_callback(rid: int, fu: Future):
            nonlocal error, runner_id
            try:
                runner_id = rid
                fu.result()
            except RuntimeError as e:
                error = str(e)

        runner = TestRunner(with_exception=True)
        thread_reaper.submit(runner_id=123,
                             fn=runner,
                             context=RunnerContext(1, RunnerInput()),
                             done_callback=done_callback)

        self.fake_time_patcher.interrupt(5)
        self.assertEqual(runner.context.index, 1)
        self.assertEqual(runner_id, 123)
        self.assertEqual(error, 'fake error')
        thread_reaper.stop(wait=True)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
