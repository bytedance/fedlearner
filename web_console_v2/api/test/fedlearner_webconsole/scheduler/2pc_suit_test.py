# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
from testing.common import multi_process_test
from scheduler_test import WorkflowTest, FollowerConfig, LeaderConfig


class MyTestCase(unittest.TestCase):

    def test_multi_process_test(self):
        multi_process_test([{'class': WorkflowTest,
                             'method': 'leader_test_workflow',
                             'config': LeaderConfig},
                            {'class': WorkflowTest,
                             'method': 'follower_test_workflow',
                             'config': FollowerConfig}])


if __name__ == '__main__':
    unittest.main()
