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
import shutil
import tempfile
import unittest

from unittest.mock import MagicMock, patch
from os.path import dirname

from envs import Envs
from fedlearner_webconsole.sparkapp.schema import SparkAppConfig
from fedlearner_webconsole.sparkapp.service import SparkAppService

BASE_DIR = Envs.BASE_DIR


class SparkAppServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._upload_path = os.path.join(BASE_DIR, 'test-spark')
        os.makedirs(self._upload_path)
        self._patch_upload_path = patch(
            'fedlearner_webconsole.sparkapp.service.UPLOAD_PATH',
            self._upload_path)
        self._patch_upload_path.start()
        self._sparkapp_service = SparkAppService()

    def tearDown(self) -> None:
        self._patch_upload_path.stop()
        shutil.rmtree(self._upload_path)
        return super().tearDown()

    def _get_tar_file_path(self) -> str:
        return os.path.join(
            BASE_DIR, 'test/fedlearner_webconsole/test_data/sparkapp.tar')

    def test_get_sparkapp_upload_path(self):
        existable, sparkapp_path = self._sparkapp_service._get_sparkapp_upload_path(
            'test')
        self.assertFalse(existable)

        os.makedirs(sparkapp_path)
        existable, _ = self._sparkapp_service._get_sparkapp_upload_path('test')
        self.assertTrue(existable)

    def test_copy_files_to_target_filesystem(self):
        _, sparkapp_path = self._sparkapp_service._get_sparkapp_upload_path(
            'test')
        self._sparkapp_service._clear_and_make_an_empty_dir(sparkapp_path)
        files_path = self._get_tar_file_path()
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = files_path.rsplit('/', 1)[-1]
            temp_file_path = os.path.join(temp_dir, file_name)
            shutil.copy(files_path, temp_file_path)
            self._sparkapp_service._copy_files_to_target_filesystem(
                source_filesystem_path=temp_file_path,
                target_filesystem_path=sparkapp_path)

            self.assertTrue(
                os.path.exists(os.path.join(sparkapp_path, 'convertor.py')))

    @patch(
        'fedlearner_webconsole.utils.k8s_client.k8s_client.create_sparkapplication'
    )
    def test_submit_sparkapp(self, mock_create_sparkapp: MagicMock):
        mock_create_sparkapp.return_value = {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp': '2021-05-18T08:59:16Z',
                'generation': 1,
                'name': 'fl-transformer-yaml',
                'namespace': 'fedlearner',
                'resourceVersion': '432649442',
                'selfLink':
                '/apis/sparkoperator.k8s.io/v1beta2/namespaces/fedlearner/sparkapplications/fl-transformer-yaml',
                'uid': '52d66d27-b7b7-11eb-b9df-b8599fdb0aac'
            },
            'spec': {
                'arguments': ['data.csv', 'data_tfrecords/'],
                'driver': {
                    'coreLimit': '4000m',
                    'cores': 1,
                    'labels': {
                        'version': '3.0.0'
                    },
                    'memory': '512m',
                    'serviceAccount': 'spark',
                },
                'dynamicAllocation': {
                    'enabled': False
                },
                'executor': {
                    'cores': 1,
                    'instances': 1,
                    'labels': {
                        'version': '3.0.0'
                    },
                    'memory': '512m',
                },
                'image': 'dockerhub.com',
                'imagePullPolicy': 'Always',
                'mainApplicationFile': 'transformer.py',
                'mode': 'cluster',
                'pythonVersion': '3',
                'restartPolicy': {
                    'type': 'Never'
                },
                'sparkConf': {
                    'spark.shuffle.service.enabled': 'false'
                },
                'sparkVersion': '3.0.0',
                'type': 'Python',
            },
            'status': {
                'applicationState': {
                    'state': 'COMPLETED'
                },
                'driverInfo': {
                    'podName': 'fl-transformer-yaml-driver',
                    'webUIAddress': '11.249.131.12:4040',
                    'webUIPort': 4040,
                    'webUIServiceName': 'fl-transformer-yaml-ui-svc'
                },
                'executionAttempts': 1,
                'executorState': {
                    'fl-transformer-yaml-bdc15979a314310b-exec-1': 'PENDING',
                    'fl-transformer-yaml-bdc15979a314310b-exec-2': 'COMPLETED'
                },
                'lastSubmissionAttemptTime': '2021-05-18T10:31:13Z',
                'sparkApplicationId': 'spark-a380bfd520164d828a334bcb3a6404f9',
                'submissionAttempts': 1,
                'submissionID': '5bc7e2e7-cc0f-420c-8bc7-138b651a1dde',
                'terminationTime': '2021-05-18T10:32:08Z'
            }
        }

        tarball_file_path = os.path.join(
            BASE_DIR, 'test/fedlearner_webconsole/test_data/sparkapp.tar')
        with open(tarball_file_path, 'rb') as f:
            files_bin = f.read()

        inputs = {
            'name': 'fl-transformer-yaml',
            'files': files_bin,
            'image_url': 'dockerhub.com',
            'driver_config': {
                'cores': 1,
                'memory': '200m',
                'coreLimit': '4000m',
            },
            'executor_config': {
                'cores': 1,
                'memory': '200m',
                'instances': 5,
            },
            'command': ['data.csv', 'data.rd'],
            'main_application': '${prefix}/convertor.py'
        }
        config = SparkAppConfig.from_dict(inputs)
        resp = self._sparkapp_service.submit_sparkapp(config)

        self.assertTrue(
            os.path.exists(
                os.path.join(self._upload_path, 'sparkapp',
                             'fl-transformer-yaml', 'convertor.py')))
        mock_create_sparkapp.assert_called_once()
        self.assertTrue(resp.namespace, 'fedlearner')

    @patch(
        'fedlearner_webconsole.utils.k8s_client.k8s_client.get_sparkapplication'
    )
    def test_get_sparkapp_info(self, mock_get_sparkapp: MagicMock):
        mock_get_sparkapp.return_value = {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp': '2021-05-18T08:59:16Z',
                'generation': 1,
                'name': 'fl-transformer-yaml',
                'namespace': 'fedlearner',
                'resourceVersion': '432649442',
                'selfLink':
                '/apis/sparkoperator.k8s.io/v1beta2/namespaces/fedlearner/sparkapplications/fl-transformer-yaml',
                'uid': '52d66d27-b7b7-11eb-b9df-b8599fdb0aac'
            },
            'spec': {
                'arguments': ['data.csv', 'data_tfrecords/'],
                'driver': {
                    'coreLimit': '4000m',
                    'cores': 1,
                    'labels': {
                        'version': '3.0.0'
                    },
                    'memory': '512m',
                    'serviceAccount': 'spark',
                },
                'dynamicAllocation': {
                    'enabled': False
                },
                'executor': {
                    'cores': 1,
                    'instances': 1,
                    'labels': {
                        'version': '3.0.0'
                    },
                    'memory': '512m',
                },
                'image': 'dockerhub.com',
                'imagePullPolicy': 'Always',
                'mainApplicationFile': 'transformer.py',
                'mode': 'cluster',
                'pythonVersion': '3',
                'restartPolicy': {
                    'type': 'Never'
                },
                'sparkConf': {
                    'spark.shuffle.service.enabled': 'false'
                },
                'sparkVersion': '3.0.0',
                'type': 'Python',
            },
            'status': {
                'applicationState': {
                    'state': 'COMPLETED'
                },
                'driverInfo': {
                    'podName': 'fl-transformer-yaml-driver',
                    'webUIAddress': '11.249.131.12:4040',
                    'webUIPort': 4040,
                    'webUIServiceName': 'fl-transformer-yaml-ui-svc'
                },
                'executionAttempts': 1,
                'executorState': {
                    'fl-transformer-yaml-bdc15979a314310b-exec-1': 'PENDING',
                    'fl-transformer-yaml-bdc15979a314310b-exec-2': 'COMPLETED'
                },
                'lastSubmissionAttemptTime': '2021-05-18T10:31:13Z',
                'sparkApplicationId': 'spark-a380bfd520164d828a334bcb3a6404f9',
                'submissionAttempts': 1,
                'submissionID': '5bc7e2e7-cc0f-420c-8bc7-138b651a1dde',
                'terminationTime': '2021-05-18T10:32:08Z'
            }
        }

        resp = self._sparkapp_service.get_sparkapp_info('fl-transformer-yaml')

        mock_get_sparkapp.assert_called_once()
        self.assertTrue(resp.namespace, 'fedlearner')

    @patch(
        'fedlearner_webconsole.sparkapp.service.SparkAppService._get_sparkapp_upload_path'
    )
    @patch('fedlearner_webconsole.utils.file_manager.FileManager.remove')
    @patch(
        'fedlearner_webconsole.utils.k8s_client.k8s_client.delete_sparkapplication'
    )
    def test_delete_sparkapp(self, mock_delete_sparkapp: MagicMock,
                             mock_file_mananger_remove: MagicMock,
                             mock_upload_path: MagicMock):
        mock_delete_sparkapp.return_value = {
            'kind': 'Status',
            'apiVersion': 'v1',
            'metadata': {},
            'status': 'Success',
            'details': {
                'name': 'fl-transformer-yaml',
                'group': 'sparkoperator.k8s.io',
                'kind': 'sparkapplications',
                'uid': '52d66d27-b7b7-11eb-b9df-b8599fdb0aac'
            }
        }
        mock_upload_path.return_value = (True, 'test')
        resp = self._sparkapp_service.delete_sparkapp(
            name='fl-transformer-yaml')
        mock_delete_sparkapp.assert_called_once()
        mock_file_mananger_remove.assert_called_once()
        self.assertTrue(resp.name, 'fl-transformer-yaml')


if __name__ == '__main__':
    unittest.main()
