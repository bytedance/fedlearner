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
from fedlearner_webconsole.dataset.scheduler.chained_executor import run_executor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorType
from testing.dataset import FakeExecutor


class ChainedExecutorTest(unittest.TestCase):

    @patch('fedlearner_webconsole.dataset.scheduler.chained_executor._get_executor')
    def test_run_executor(self, mock_get_executor: MagicMock):
        mock_get_executor.return_value = FakeExecutor()
        executor_resutls = run_executor(executor_type=ExecutorType.CRON_DATASET_JOB)
        self.assertEqual(executor_resutls.succeeded_item_ids, [1])
        self.assertEqual(executor_resutls.failed_item_ids, [2, 4])
        self.assertEqual(executor_resutls.skip_item_ids, [3])
        mock_get_executor.assert_called_once_with(executor_type=ExecutorType.CRON_DATASET_JOB)


if __name__ == '__main__':
    unittest.main()
