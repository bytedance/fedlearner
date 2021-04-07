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
import logging
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from testing.common import BaseTestCase


class SettingsApiTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        START_GRPC_SERVER = False
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        self._deployment = SimpleNamespace(**{
            'metadata': SimpleNamespace(**{
                'name': 'fedlearner-web-console-v2',
                'namespace': 'testns'
            }),
            'spec': SimpleNamespace(**{
                'template': SimpleNamespace(**{
                    'spec': SimpleNamespace(**{
                        'containers': [SimpleNamespace(**{
                            'image': 'fedlearner:test'
                        })]
                    })
                })
            })
        })
        self._mock_k8s_client = MagicMock()
        self._mock_k8s_client.get_deployment = MagicMock(
            return_value=self._deployment)
        self.signin_as_admin()

    @patch('fedlearner_webconsole.setting.apis._POD_NAMESPACE', 'testns')
    def test_get_settings(self):
        with patch('fedlearner_webconsole.setting.apis.get_client',
                   return_value=self._mock_k8s_client):
            response_data = self.get_response_data(
                self.get_helper('/api/v2/settings'))
            self.assertEqual(response_data, {
                'webconsole_image': 'fedlearner:test'
            })
            self._mock_k8s_client.get_deployment.assert_called_with(
                name='fedlearner-web-console-v2',
                namespace='testns'
            )

    def test_update_image(self):
        self._mock_k8s_client.create_or_update_deployment = MagicMock()
        with patch('fedlearner_webconsole.setting.apis.get_client',
                   return_value=self._mock_k8s_client):
            resp = self.patch_helper(
                '/api/v2/settings',
                data={
                    'webconsole_image': 'test-new-image'
                })
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            _, kwargs = self._mock_k8s_client.create_or_update_deployment.call_args
            self.assertEqual(kwargs['spec'].template.spec.containers[0].image,
                             'test-new-image')
            self.assertEqual(kwargs['name'], self._deployment.metadata.name)
            self.assertEqual(kwargs['namespace'],
                             self._deployment.metadata.namespace)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
