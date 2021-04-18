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

import unittest

from test.fedlearner_webconsole.composer.common import TaskRunner
from testing.common import BaseTestCase

from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.runner_cache import RunnerCache


class RunnerCacheTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        STORAGE_ROOT = '/tmp'
        START_SCHEDULER = False
        START_GRPC_SERVER = False

    def test_runner(self):
        c = RunnerCache(runner_fn={
            ItemType.TASK.value: TaskRunner,
        })
        runners = [
            (1, 'task_1'),
            (2, 'task_2'),
            (3, 'task_3'),
        ]
        for runner in runners:
            rid, name = runner
            c.find_runner(rid, name)
        self.assertEqual(len(runners), len(c.data),
                         'should be equal runners number')

        for runner in runners:
            rid, name = runner
            c.del_runner(rid, name)
        self.assertEqual(0, len(c.data), 'should be equal 0')


if __name__ == '__main__':
    unittest.main()
