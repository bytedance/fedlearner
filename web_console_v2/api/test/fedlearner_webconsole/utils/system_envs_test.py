# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import os
import unittest
from unittest.mock import patch

from fedlearner_webconsole.utils.system_envs import get_system_envs


class SystemEnvsTest(unittest.TestCase):
    @patch.dict(os.environ, {
        'ES_HOST': 'test es host',
        'ES_PORT': '9200',
        'DB_HOST': 'test db host',
        'DB_PORT': '3306',
        'DB_DATABASE': 'fedlearner',
        'DB_USERNAME': 'username',
        'DB_PASSWORD': 'password',
        'KVSTORE_TYPE': 'mysql'
    })
    def test_get_system_envs(self):
        self.assertEqual(
            get_system_envs(),
            '{"name": "POD_IP", "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}},'
            '{"name": "POD_NAME", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},'
            '{"name": "CPU_REQUEST", "valueFrom": {"resourceFieldRef": {"resource": "requests.cpu"}}},'
            '{"name": "MEM_REQUEST", "valueFrom": {"resourceFieldRef": {"resource": "requests.memory"}}},'
            '{"name": "CPU_LIMIT", "valueFrom": {"resourceFieldRef": {"resource": "limits.cpu"}}},'
            '{"name": "MEM_LIMIT", "valueFrom": {"resourceFieldRef": {"resource": "limits.memory"}}},'
            '{"name": "ES_HOST", "value": "test es host"},'
            '{"name": "ES_PORT", "value": "9200"},'
            '{"name": "DB_HOST", "value": "test db host"},'
            '{"name": "DB_PORT", "value": "3306"},'
            '{"name": "DB_DATABASE", "value": "fedlearner"},'
            '{"name": "DB_USERNAME", "value": "username"},'
            '{"name": "DB_PASSWORD", "value": "password"},'
            '{"name": "KVSTORE_TYPE", "value": "mysql"}')


if __name__ == '__main__':
    unittest.main()
