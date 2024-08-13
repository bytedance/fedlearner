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
from datetime import timezone, datetime
from unittest.mock import MagicMock, patch
from testing.no_web_server_test_case import NoWebServerTestCase
from testing.fake_time_patcher import FakeTimePatcher

from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput

from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.cleanup.models import Cleanup, CleanupState, ResourceType
from fedlearner_webconsole.cleanup.cleaner_cronjob import CleanupCronJob
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupPayload


@patch('fedlearner_webconsole.utils.file_manager.FileManager.exists')
@patch('fedlearner_webconsole.utils.file_manager.FileManager.remove')
class CleanupCronJobTest(NoWebServerTestCase):
    _CLEANUP_ID = 1

    def setUp(self):
        super().setUp()
        self.time_patcher = FakeTimePatcher()
        self.time_patcher.start(datetime(2012, 1, 14, 12, 0, 5, tzinfo=timezone.utc))
        self.default_paylaod = CleanupPayload(paths=['/Major333/test_path/a.csv'])
        with db.session_scope() as session:
            self.default_cleanup = Cleanup(id=1,
                                           state=CleanupState.WAITING,
                                           target_start_at=datetime(1999, 3, 1, tzinfo=timezone.utc),
                                           resource_id=1,
                                           resource_type=ResourceType(Dataset).name,
                                           payload=self.default_paylaod)
            session.add(self.default_cleanup)
            session.commit()

    def tearDown(self):
        self.time_patcher.stop()
        super().tearDown()

    def test_run_failed_alone(self, mock_remove: MagicMock, mock_exists: MagicMock):
        # The file always exist
        mock_exists.return_value = True
        #Failed to delete
        mock_remove.side_effect = RuntimeError('fake error')

        runner = CleanupCronJob()
        runner_input = RunnerInput()
        runner_context = RunnerContext(index=0, input=runner_input)

        status, output = runner.run(runner_context)
        self.assertEqual(status, RunnerStatus.DONE)
        expected_cleanup_status = CleanupState.FAILED
        with db.session_scope() as session:
            cleanup = session.query(Cleanup).get(1)
        self.assertEqual(expected_cleanup_status, cleanup.state)

    def test_run_success_alone(self, mock_remove: MagicMock, mock_exists: MagicMock):
        # The file always exist
        mock_exists.return_value = True
        #Success to delete
        mock_remove.reset_mock(side_effect=True)

        runner = CleanupCronJob()
        runner_input = RunnerInput()
        runner_context = RunnerContext(index=0, input=runner_input)

        status, output = runner.run(runner_context)
        self.assertEqual(status, RunnerStatus.DONE)
        expected_cleanup_status = CleanupState.SUCCEEDED
        with db.session_scope() as session:
            cleanup = session.query(Cleanup).get(1)
        self.assertEqual(expected_cleanup_status, cleanup.state)


if __name__ == '__main__':
    unittest.main()
