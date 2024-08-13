# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client import ApiException

from fedlearner_webconsole.k8s.k8s_client import K8sClient, REQUEST_TIMEOUT_IN_SECOND


class K8sClientTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self._load_incluster_config_patcher = patch(
            'fedlearner_webconsole.k8s.k8s_client.kubernetes.config.load_incluster_config', lambda: None)
        self._load_incluster_config_patcher.start()

        self._k8s_client = K8sClient()
        self._k8s_client.init()

    def tearDown(self):
        self._load_incluster_config_patcher.stop()
        super().tearDown()

    def test_delete_flapp(self):
        mock_crds = MagicMock()
        self._k8s_client.crds = mock_crds
        # Test delete successfully
        mock_crds.delete_namespaced_custom_object = MagicMock()
        self._k8s_client.delete_app('test_flapp', 'fedlearner.k8s.io', 'v1alpha1', 'flapps')
        mock_crds.delete_namespaced_custom_object.assert_called_once_with(group='fedlearner.k8s.io',
                                                                          name='test_flapp',
                                                                          namespace='default',
                                                                          plural='flapps',
                                                                          version='v1alpha1',
                                                                          _request_timeout=REQUEST_TIMEOUT_IN_SECOND)
        # Tests that the flapp has been deleted
        mock_crds.delete_namespaced_custom_object = MagicMock(side_effect=ApiException(status=404))
        self._k8s_client.delete_app('test_flapp2', 'fedlearner.k8s.io', 'v1alpha1', 'flapps')
        self.assertEqual(mock_crds.delete_namespaced_custom_object.call_count, 1)
        # Tests with other exceptions
        mock_crds.delete_namespaced_custom_object = MagicMock(side_effect=ApiException(status=500))
        with self.assertRaises(RuntimeError):
            self._k8s_client.delete_app('test_flapp3', 'fedlearner.k8s.io', 'v1alpha1', 'flapps')
        self.assertEqual(mock_crds.delete_namespaced_custom_object.call_count, 3)

    def test_create_flapp(self):
        test_yaml = {'metadata': {'name': 'test app'}, 'kind': 'flapp', 'apiVersion': 'fedlearner.k8s.io/v1alpha1'}
        mock_crds = MagicMock()
        self._k8s_client.crds = mock_crds
        # Test create successfully
        mock_crds.create_namespaced_custom_object = MagicMock()
        self._k8s_client.create_app(test_yaml, plural='flapps', version='v1alpha1', group='fedlearner.k8s.io')
        mock_crds.create_namespaced_custom_object.assert_called_once_with(group='fedlearner.k8s.io',
                                                                          namespace='default',
                                                                          plural='flapps',
                                                                          version='v1alpha1',
                                                                          _request_timeout=REQUEST_TIMEOUT_IN_SECOND,
                                                                          body=test_yaml)
        self._k8s_client.create_app(test_yaml, plural='flapps', version='v1alpha1', group='fedlearner.k8s.io')
        self.assertEqual(mock_crds.create_namespaced_custom_object.call_count, 2)

    @patch('fedlearner_webconsole.k8s.k8s_client.parse_and_get_fn')
    @patch('fedlearner_webconsole.k8s.k8s_client.client.CustomObjectsApi.create_namespaced_custom_object')
    def test_create_app_with_hook(self, mock_create_namespaced_custom_object: MagicMock,
                                  mock_parse_and_get_fn: MagicMock):

        def custom_magic_fn(app_yaml: dict) -> dict:
            app_yaml['metadata']['name'] = app_yaml['metadata']['name'] + '_hello'
            return app_yaml

        mock_parse_and_get_fn.return_value = custom_magic_fn
        self._k8s_client.init(hook_module_path='test.hook:custom_magic_fn')
        deployment_app_yaml = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': 'world',
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': 'test-app'
                    }
                },
                'replicas': 1,
                'template': {
                    'metadata': {
                        'labels': {
                            'app': 'test-app'
                        }
                    },
                    'spec': {
                        'volumes': [{
                            'name': 'test-app-config',
                            'configMap': {
                                'name': 'test-app-config'
                            }
                        }],
                        'containers': [{
                            'name': 'test-app',
                            'image': 'serving:lastest',
                            'args': [
                                '--port=8500', '--rest_api_port=8501', '--model_config_file=/app/config/config.pb'
                            ],
                            'ports': [{
                                'containerPort': 8500
                            }, {
                                'containerPort': 8501
                            }],
                            'volumeMounts': [{
                                'name': 'test-app-config',
                                'mountPath': '/app/config/'
                            }]
                        }]
                    }
                }
            }
        }
        self._k8s_client.create_app(app_yaml=deployment_app_yaml, group='apps', version='v1', plural='Deployment')

        mock_parse_and_get_fn.assert_called_once_with('test.hook:custom_magic_fn')
        mock_create_namespaced_custom_object.assert_called_once()
        self.assertEqual(mock_create_namespaced_custom_object.call_args[1]['body']['metadata']['name'], 'world_hello')


if __name__ == '__main__':
    unittest.main()
