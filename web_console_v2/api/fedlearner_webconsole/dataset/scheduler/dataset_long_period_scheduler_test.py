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
from unittest.mock import MagicMock, patch

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult, ExecutorType
from fedlearner_webconsole.dataset.scheduler.dataset_long_period_scheduler import DatasetLongPeriodScheduler
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.proto.composer_pb2 import DatasetSchedulerOutput, ExecutorResults, RunnerInput, RunnerOutput


class DatasetLongPeriodSchedulerTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.CronDatasetJobExecutor.get_item_ids')
    @patch('fedlearner_webconsole.dataset.scheduler.update_auth_status_executor.UpdateAuthStatusExecutor.get_item_ids')
    @patch('fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.CronDatasetJobExecutor.run_item')
    @patch('fedlearner_webconsole.dataset.scheduler.update_auth_status_executor.UpdateAuthStatusExecutor.run_item')
    def test_run(self, mock_update_auth_status_run_item: MagicMock, mock_cron_dataset_job_run_item: MagicMock,
                 mock_update_auth_status_get_item_ids: MagicMock, mock_cron_dataset_job_get_item_ids: MagicMock):
        mock_cron_dataset_job_get_item_ids.return_value = [1, 2, 3, 4]
        mock_cron_dataset_job_run_item.side_effect = [
            ExecutorResult.SUCCEEDED, ExecutorResult.SUCCEEDED, ExecutorResult.FAILED, ExecutorResult.SKIP
        ]
        mock_update_auth_status_get_item_ids.return_value = [1, 2]
        mock_update_auth_status_run_item.side_effect = [ExecutorResult.FAILED, ExecutorResult.FAILED]
        dataset_long_period_scheduler = DatasetLongPeriodScheduler()
        status, runner_output = dataset_long_period_scheduler.run(context=RunnerContext(0, RunnerInput()))
        self.assertEqual(status, RunnerStatus.DONE)
        expected_runner_output = RunnerOutput(dataset_scheduler_output=DatasetSchedulerOutput(
            executor_outputs={
                ExecutorType.CRON_DATASET_JOB.value:
                    ExecutorResults(succeeded_item_ids=[1, 2], failed_item_ids=[3], skip_item_ids=[4]),
                ExecutorType.UPDATE_AUTH_STATUS.value:
                    ExecutorResults(failed_item_ids=[1, 2]),
            }))
        self.assertEqual(runner_output, expected_runner_output)


if __name__ == '__main__':
    unittest.main()
