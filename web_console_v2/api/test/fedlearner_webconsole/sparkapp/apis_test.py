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
import os
import unittest
import base64
from unittest import mock

from unittest.mock import MagicMock, patch
from os.path import dirname
from fedlearner_webconsole.sparkapp.schema import SparkAppInfo

from testing.common import BaseTestCase
from envs import Envs

BASE_DIR = Envs.BASE_DIR


class SparkAppApiTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._upload_path = os.path.join(BASE_DIR, 'test')
        self._upload_path_patcher = patch(
            'fedlearner_webconsole.sparkapp.service.UPLOAD_PATH',
            self._upload_path)
        self._upload_path_patcher.start()

    def tearDown(self):
        self._upload_path_patcher.stop()
        super().tearDown()

    @patch(
        'fedlearner_webconsole.sparkapp.service.SparkAppService.submit_sparkapp'
    )
    def test_submit_sparkapp(self, mock_submit_sparkapp: MagicMock):
        mock_submit_sparkapp.return_value = SparkAppInfo()
        tarball_file_path = os.path.join(
            BASE_DIR, 'test/fedlearner_webconsole/test_data/sparkapp.tar')
        with open(tarball_file_path, 'rb') as f:
            files_bin = f.read()

        self.post_helper(
            '/api/v2/sparkapps', {
                'name': 'fl-transformer-yaml',
                'files': base64.b64encode(files_bin).decode(),
                'image_url': 'dockerhub.com',
                'driver_config': {
                    'cores': 1,
                    'memory': '200m',
                    'core_limit': '4000m',
                },
                'executor_config': {
                    'cores': 1,
                    'memory': '200m',
                    'instances': 5,
                },
                'command': ['data.csv', 'data.rd'],
                'main_application': '${prefix}/convertor.py'
            }).json

        mock_submit_sparkapp.assert_called_once()
        _, kwargs = mock_submit_sparkapp.call_args
        self.assertTrue(kwargs['config'].name, 'fl-transformer-yaml')

    @patch(
        'fedlearner_webconsole.sparkapp.service.SparkAppService.get_sparkapp_info'
    )
    def test_get_sparkapp_info(self, mock_get_sparkapp: MagicMock):
        mock_get_sparkapp.return_value = SparkAppInfo()

        self.get_helper('/api/v2/sparkapps/fl-transformer-yaml').json

        mock_get_sparkapp.assert_called_once_with('fl-transformer-yaml')

    @patch(
        'fedlearner_webconsole.sparkapp.service.SparkAppService.delete_sparkapp'
    )
    def test_delete_sparkapp(self, mock_delete_sparkapp: MagicMock):
        mock_delete_sparkapp.return_value = SparkAppInfo()
        resp = self.delete_helper('/api/v2/sparkapps/fl-transformer-yaml').json
        mock_delete_sparkapp.assert_called_once_with('fl-transformer-yaml')


if __name__ == '__main__':
    unittest.main()
