# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.proto import sparkapp_pb2
from fedlearner_webconsole.sparkapp.schema import SparkAppConfig, SparkPodConfig, from_k8s_resp


class SparkAppSchemaTest(NoWebServerTestCase):

    def test_spark_pod_config(self):
        inputs = {'cores': 1, 'memory': '200m', 'core_limit': '4000m', 'envs': {'HELLO': '1'}}
        spark_pod_config = SparkPodConfig.from_dict(inputs)
        config = spark_pod_config.build_config()
        self.assertDictEqual(config, {
            'cores': 1,
            'memory': '200m',
            'coreLimit': '4000m',
            'env': [{
                'name': 'HELLO',
                'value': '1'
            }]
        })

    def test_sparkapp_config(self):
        inputs = {
            'name': 'test',
            'files': bytes(100),
            'image_url': 'dockerhub.com',
            'driver_config': {
                'cores': 1,
                'memory': '200m',
                'core_limit': '4000m',
                'envs': {
                    'HELLO': '1'
                },
                'volumeMounts': [{
                    'mountPath': '/data',
                    'name': 'data'
                }]
            },
            'executor_config': {
                'cores': 1,
                'memory': '200m',
                'instances': 64,
                'envs': {
                    'HELLO': '1'
                },
                'volumeMounts': [{
                    'mountPath': '/data',
                    'name': 'data',
                    'unknown': '2',
                }]
            },
            'command': ['hhh', 'another'],
            'main_application': '${prefix}/main.py',
            'volumes': [{
                'name': 'data',
                'hostPath': {
                    'path': '/data',
                },
                'unknown': '1',
            }]
        }
        sparkapp_config = SparkAppConfig.from_dict(inputs)
        config = sparkapp_config.build_config('./test')
        self.assertEqual(config['spec']['mainApplicationFile'], './test/main.py')
        self.assertNotIn('instances', config['spec']['driver'])
        self.assertEqual([{'name': 'data', 'hostPath': {'path': '/data',}}], config['spec']['volumes'])
        self.assertEqual(config['spec']['executor']['instances'], 30)
        self.assertEqual(config['spec']['dynamicAllocation']['maxExecutors'], 64)

    def test_sparkapp_dynamic_allocation(self):
        inputs = {
            'name': 'test',
            'image_url': 'test.com/test/hhh:1',
            'dynamic_allocation': {
                'enabled': True,
                'initialExecutors': 2,
                'minExecutors': 2,
                'maxExecutors': 10
            }
        }
        sparkapp_config: SparkAppConfig = SparkAppConfig.from_dict(inputs)
        config = sparkapp_config.build_config('./test')
        print(config['spec']['dynamicAllocation'])
        self.assertEqual(len(config['spec']['dynamicAllocation']), 4)
        self.assertTrue(config['spec']['dynamicAllocation']['enabled'])

    def test_sparkapp_info(self):
        resp = {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp':
                    '2021-05-18T08:59:16Z',
                'generation':
                    1,
                'name':
                    'fl-transformer-yaml',
                'namespace':
                    'fedlearner',
                'resourceVersion':
                    '432649442',
                'selfLink':
                    '/apis/sparkoperator.k8s.io/v1beta2/namespaces/fedlearner/sparkapplications/fl-transformer-yaml',
                'uid':
                    '52d66d27-b7b7-11eb-b9df-b8599fdb0aac'
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
                    'volumeMounts': [{
                        'mountPath': '/data',
                        'name': 'data',
                        'readOnly': True
                    }],
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
                    'volumeMounts': [{
                        'mountPath': '/data',
                        'name': 'data',
                        'readOnly': True
                    }],
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

        sparkapp_info = from_k8s_resp(resp)
        self.assertEqual(sparkapp_info.namespace, 'fedlearner')
        self.assertEqual(sparkapp_info.name, 'fl-transformer-yaml')
        self.assertEqual(sparkapp_info.driver.volume_mounts[0],
                         sparkapp_pb2.VolumeMount(mount_path='/data', name='data', read_only=True))
        self.assertEqual(sparkapp_info.executor.volume_mounts[0],
                         sparkapp_pb2.VolumeMount(mount_path='/data', name='data', read_only=True))


if __name__ == '__main__':
    unittest.main()
