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
from unittest.mock import patch

from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import SchedulerRunner, RunnerStatus
from fedlearner_webconsole.composer.pipeline import PipelineExecutor
from fedlearner_webconsole.composer.thread_reaper import ThreadReaper
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import composer_pb2
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, PipelineContextData, RunnerOutput
from testing.composer.common import TestRunner
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.fake_time_patcher import FakeTimePatcher

_RUNNER_FNS = {
    ItemType.TASK.value: TestRunner,
}


class PipelineExecutorTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.thread_reaper = ThreadReaper(worker_num=1)
        self.executor = PipelineExecutor(self.thread_reaper, db.engine, _RUNNER_FNS)

        self.time_patcher = FakeTimePatcher()
        self.time_patcher.start(datetime(2012, 1, 14, 12, 0, 5))

    def tearDown(self):
        self.time_patcher.stop()
        self.thread_reaper.stop(wait=True)
        super().tearDown()

    def test_run_completed(self):
        runner = SchedulerRunner(item_id=123, status=RunnerStatus.RUNNING.value)
        runner.set_pipeline(
            composer_pb2.Pipeline(version=2, name='test pipeline',
                                  queue=[RunnerInput(runner_type=ItemType.TASK.value)]))
        with db.session_scope() as session:
            session.add(runner)
            session.commit()
        self.executor.run(runner.id)
        self.time_patcher.interrupt(60)
        with db.session_scope() as session:
            runner = session.query(SchedulerRunner).get(runner.id)
            self.assertEqual(runner.status, RunnerStatus.DONE.value)
            self.assertEqual(runner.get_context(), PipelineContextData(current_runner=0, outputs={0: RunnerOutput()}))

    def test_run_failed(self):
        runner = SchedulerRunner(item_id=123, status=RunnerStatus.RUNNING.value)
        runner.set_pipeline(
            composer_pb2.Pipeline(
                version=2,
                name='test failed pipeline',
                queue=[
                    RunnerInput(runner_type=ItemType.TASK.value),
                    RunnerInput(runner_type=ItemType.TASK.value),
                    RunnerInput(runner_type=ItemType.TASK.value),
                    # Failed one
                    RunnerInput(runner_type=ItemType.TASK.value),
                    RunnerInput(runner_type=ItemType.TASK.value),
                ]))
        runner.set_context(composer_pb2.PipelineContextData(current_runner=3))
        with db.session_scope() as session:
            session.add(runner)
            session.commit()
        self.executor.run(runner.id)
        self.time_patcher.interrupt(60)
        with db.session_scope() as session:
            runner = session.query(SchedulerRunner).get(runner.id)
            self.assertEqual(runner.status, RunnerStatus.FAILED.value)
            self.assertEqual(
                runner.get_context(),
                PipelineContextData(current_runner=3, outputs={3: RunnerOutput(error_message='index is 3')}))

    @patch('testing.composer.common.TestRunner.run')
    def test_run_exception(self, mock_run):

        def fake_run(*args, **kwargs):
            raise RuntimeError('fake exception')

        mock_run.side_effect = fake_run

        runner = SchedulerRunner(item_id=666, status=RunnerStatus.RUNNING.value)
        runner.set_pipeline(
            composer_pb2.Pipeline(
                version=2,
                name='test failed pipeline',
                queue=[
                    # Exception one
                    RunnerInput(runner_type=ItemType.TASK.value),
                ]))
        runner.set_context(composer_pb2.PipelineContextData(current_runner=0))
        with db.session_scope() as session:
            session.add(runner)
            session.commit()
        self.executor.run(runner.id)
        self.time_patcher.interrupt(60)
        with db.session_scope() as session:
            runner = session.query(SchedulerRunner).get(runner.id)
            self.assertEqual(runner.status, RunnerStatus.FAILED.value)
            self.assertEqual(
                runner.get_context(),
                PipelineContextData(current_runner=0, outputs={0: RunnerOutput(error_message='fake exception')}))

    def test_run_second_runner(self):
        runner = SchedulerRunner(item_id=123, status=RunnerStatus.RUNNING.value)
        runner.set_pipeline(
            composer_pb2.Pipeline(version=2,
                                  name='test running pipeline',
                                  queue=[
                                      RunnerInput(runner_type=ItemType.TASK.value),
                                      RunnerInput(runner_type=ItemType.TASK.value),
                                      RunnerInput(runner_type=ItemType.TASK.value),
                                  ]))
        runner.set_context(composer_pb2.PipelineContextData(current_runner=1))
        with db.session_scope() as session:
            session.add(runner)
            session.commit()
        self.executor.run(runner.id)
        self.time_patcher.interrupt(60)
        with db.session_scope() as session:
            runner = session.query(SchedulerRunner).get(runner.id)
            self.assertEqual(runner.status, RunnerStatus.RUNNING.value)
            self.assertEqual(runner.get_context(), PipelineContextData(current_runner=2, outputs={1: RunnerOutput()}))


if __name__ == '__main__':
    unittest.main()
