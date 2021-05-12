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
from unittest.mock import MagicMock

from kubernetes.client import ApiException

from fedlearner_webconsole.utils.k8s_client import K8sClient


class K8sClientTest(unittest.TestCase):
    def setUp(self):
        self._k8s_client = K8sClient()

    def test_delete_flapp(self):
        mock_crds = MagicMock()
        self._k8s_client.crds = mock_crds
        # Test delete successfully
        mock_crds.delete_namespaced_custom_object = MagicMock()
        self._k8s_client.delete_flapp('test_flapp')
        mock_crds.delete_namespaced_custom_object.assert_called_once_with(
            group='fedlearner.k8s.io',
            name='test_flapp',
            namespace='default',
            plural='flapps',
            version='v1alpha1')
        # Tests that the flapp has been deleted
        mock_crds.delete_namespaced_custom_object = MagicMock(
            side_effect=ApiException(status=404))
        self._k8s_client.delete_flapp('test_flapp2')
        self.assertEqual(mock_crds.delete_namespaced_custom_object.call_count,
                         1)
        # Tests with other exceptions
        mock_crds.delete_namespaced_custom_object = MagicMock(
            side_effect=ApiException(status=500))
        with self.assertRaises(RuntimeError):
            self._k8s_client.delete_flapp('test_flapp3')
        self.assertEqual(mock_crds.delete_namespaced_custom_object.call_count,
                         3)

    def test_create_flapp(self):
        test_yaml = {
            'metadata': {
                'name': 'test app'
            }
        }
        mock_crds = MagicMock()
        self._k8s_client.crds = mock_crds
        # Test create successfully
        mock_crds.create_namespaced_custom_object = MagicMock()
        self._k8s_client.create_flapp(test_yaml)
        mock_crds.create_namespaced_custom_object.assert_called_once_with(
            group='fedlearner.k8s.io',
            namespace='default',
            plural='flapps',
            version='v1alpha1',
            body=test_yaml)
        # Test that flapp exists
        mock_crds.create_namespaced_custom_object = MagicMock(
            side_effect=[ApiException(status=409), None])
        self._k8s_client.delete_flapp = MagicMock()
        self._k8s_client.create_flapp(test_yaml)
        self._k8s_client.delete_flapp.assert_called_once_with('test app')
        self.assertEqual(mock_crds.create_namespaced_custom_object.call_count,
                         2)
        # Test with other exceptions
        mock_crds.create_namespaced_custom_object = MagicMock(
            side_effect=ApiException(status=114))
        with self.assertRaises(ApiException):
            self._k8s_client.create_flapp(test_yaml)
        self.assertEqual(mock_crds.create_namespaced_custom_object.call_count,
                         3)


if __name__ == '__main__':
    unittest.main()
