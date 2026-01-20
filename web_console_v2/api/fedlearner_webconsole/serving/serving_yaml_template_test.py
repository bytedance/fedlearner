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
from unittest.mock import patch

from google.protobuf.text_format import Parse
from tensorflow_serving.config.model_server_config_pb2 import ModelServerConfig

from fedlearner_webconsole.db import db
from fedlearner_webconsole.serving.serving_yaml_template import (CONFIG_MAP_TEMPLATE, DEPLOYMENT_TEMPLATE,
                                                                 SERVICE_TEMPLATE, generate_serving_yaml)


class ServingYamlTemplateTest(unittest.TestCase):

    def setUp(self):

        self.patcher_generate_system_dict = patch(
            'fedlearner_webconsole.serving.serving_yaml_template.GenerateDictService.generate_system_dict')
        mock = self.patcher_generate_system_dict.start()
        mock.return_value = {
            'basic_envs_list': {
                'name': 'HADOOP_HOME',
                'value': '/hadoop/'
            },
            'variables': {
                'labels': {},
                'serving_image': 'dockerhub.com/fedlearner/serving:latest',
                'volumes_list': [{}],
                'volume_mounts_list': [{}],
            }
        }

        self.serving = {
            'project': None,
            'model': {
                'base_path': '/test',
            },
            'serving': {
                'name': 'serving-demo',
                'resource': {
                    'resource': {
                        'cpu': '4000m',
                        'memory': '4Gi',
                    },
                    'replicas': 2,
                },
            },
        }
        return super().setUp()

    def tearDown(self):
        self.patcher_generate_system_dict.stop()
        return super().tearDown()

    def test_config_map(self):
        with db.session_scope() as session:
            config_map_object = generate_serving_yaml(self.serving, CONFIG_MAP_TEMPLATE, session)
        config = Parse(config_map_object['data']['config.pb'], ModelServerConfig())
        self.assertEqual(config.model_config_list.config[0].base_path, '/test')

    def test_deployment(self):
        with db.session_scope() as session:
            deployment_object = generate_serving_yaml(self.serving, DEPLOYMENT_TEMPLATE, session)
        self.assertEqual('4000m',
                         deployment_object['spec']['template']['spec']['containers'][0]['resources']['limits']['cpu'])
        self.assertEqual('serving-demo', deployment_object['metadata']['name'])
        self.assertEqual('4000m', deployment_object['metadata']['annotations']['resource-cpu'])
        self.assertEqual('4Gi', deployment_object['metadata']['annotations']['resource-mem'])

    def test_service(self):
        with db.session_scope() as session:
            service_object = generate_serving_yaml(self.serving, SERVICE_TEMPLATE, session)
        self.assertEqual('serving-demo', service_object['metadata']['name'])


if __name__ == '__main__':
    unittest.main()
