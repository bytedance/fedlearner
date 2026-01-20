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
from datetime import datetime, timezone
from unittest.mock import patch

from fedlearner_webconsole.composer.models import SchedulerItem, ItemStatus, RunnerStatus, SchedulerRunner
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import composer_pb2
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.proto import to_json
from testing.no_web_server_test_case import NoWebServerTestCase


class SchedulerItemTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        self.default_pipeline = composer_pb2.Pipeline(version=2,
                                                      name='test pipeline',
                                                      queue=[
                                                          composer_pb2.RunnerInput(runner_type='test type1'),
                                                          composer_pb2.RunnerInput(runner_type='test type2'),
                                                      ])
        scheduler_item = SchedulerItem(id=5,
                                       name='test_item_off',
                                       pipeline=to_json(self.default_pipeline),
                                       status=ItemStatus.OFF.value,
                                       cron_config='* * * * * 15',
                                       last_run_at=created_at,
                                       retry_cnt=0,
                                       created_at=created_at,
                                       updated_at=created_at)
        with db.session_scope() as session:
            session.add(scheduler_item)
            session.commit()

    def test_need_run_normal_job(self):
        with db.session_scope() as session:
            item = SchedulerItem(name='test normal item')
            session.commit()
            # Never run
            self.assertTrue(item.need_run())
            item.last_run_at = now()
            session.commit()
            self.assertFalse(item.need_run())

    @patch('fedlearner_webconsole.composer.models.now')
    def test_need_run_cron_job(self, mock_now):
        with db.session_scope() as session:
            item = SchedulerItem(
                name='test cron item',
                # Runs every 30 minutes
                cron_config='*/30 * * * *',
                created_at=datetime(2021, 9, 1, 10, 10))
            session.commit()
            # Never run
            mock_now.return_value = datetime(2021, 9, 1, 10, 20, tzinfo=timezone.utc)
            self.assertFalse(item.need_run())
            mock_now.return_value = datetime(2021, 9, 1, 10, 50, tzinfo=timezone.utc)
            self.assertTrue(item.need_run())
            # Has been run
            item.last_run_at = datetime(2021, 9, 1, 10, 10)
            session.commit()
            mock_now.return_value = datetime(2021, 9, 1, 10, 11, tzinfo=timezone.utc)
            self.assertFalse(item.need_run())
            mock_now.return_value = datetime(2021, 9, 1, 10, 50, tzinfo=timezone.utc)
            self.assertTrue(item.need_run())

    def test_get_pipeline(self):
        with db.session_scope() as session:
            scheduler_item = session.query(SchedulerItem).first()
            self.assertEqual(self.default_pipeline, scheduler_item.get_pipeline())

    def test_set_pipeline(self):
        with db.session_scope() as session:
            scheduler_item = session.query(SchedulerItem).first()
            pipeline = composer_pb2.Pipeline(name='test1')
            scheduler_item.set_pipeline(pipeline)
            self.assertEqual(pipeline, scheduler_item.get_pipeline())

    def test_to_proto(self):
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        with db.session_scope() as session:
            scheduler_item = session.query(SchedulerItem).first()
            self.assertEqual(
                scheduler_item.to_proto(),
                composer_pb2.SchedulerItemPb(id=5,
                                             name='test_item_off',
                                             pipeline=self.default_pipeline,
                                             status=ItemStatus.OFF.name,
                                             cron_config='* * * * * 15',
                                             last_run_at=int(created_at.timestamp()),
                                             retry_cnt=0,
                                             created_at=int(created_at.timestamp()),
                                             updated_at=int(created_at.timestamp())))


class SchedulerRunnerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.default_context = composer_pb2.PipelineContextData(current_runner=0)
        self.default_pipeline = composer_pb2.Pipeline(version=2,
                                                      name='test pipeline',
                                                      queue=[
                                                          composer_pb2.RunnerInput(runner_type='test type1'),
                                                          composer_pb2.RunnerInput(runner_type='test type2'),
                                                      ])
        self.default_output = composer_pb2.RunnerOutput(error_message='error1')
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        scheduler_runner = SchedulerRunner(
            id=5,
            item_id=1,
            status=RunnerStatus.INIT.value,
            start_at=created_at,
            pipeline=to_json(self.default_pipeline),
            output=to_json(self.default_output),
            context=to_json(self.default_context),
            created_at=created_at,
            updated_at=created_at,
        )
        with db.session_scope() as session:
            session.add(scheduler_runner)
            session.commit()

    def test_get_pipeline(self):
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            self.assertEqual(self.default_pipeline, scheduler_runner.get_pipeline())

    def test_set_pipeline(self):
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            pipeline = composer_pb2.Pipeline(name='test1')
            scheduler_runner.set_pipeline(pipeline)
            self.assertEqual(pipeline, scheduler_runner.get_pipeline())

    def test_get_context(self):
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            self.assertEqual(self.default_context, scheduler_runner.get_context())

    def test_set_context(self):
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            context = composer_pb2.PipelineContextData(current_runner=1)
            scheduler_runner.set_context(context)
            self.assertEqual(context, scheduler_runner.get_context())

    def test_get_output(self):
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            self.assertEqual(self.default_output, scheduler_runner.get_output())

    def test_set_output(self):
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            output = composer_pb2.RunnerOutput(error_message='error2')
            scheduler_runner.set_output(output)
            self.assertEqual(output, scheduler_runner.get_output())

    def test_to_proto(self):
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        with db.session_scope() as session:
            scheduler_runner = session.query(SchedulerRunner).first()
            self.assertEqual(
                scheduler_runner.to_proto(),
                composer_pb2.SchedulerRunnerPb(id=5,
                                               item_id=1,
                                               status=RunnerStatus.INIT.name,
                                               start_at=int(created_at.timestamp()),
                                               pipeline=self.default_pipeline,
                                               output=self.default_output,
                                               context=self.default_context,
                                               created_at=int(created_at.timestamp()),
                                               updated_at=int(created_at.timestamp())))


if __name__ == '__main__':
    unittest.main()
