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
import json
from google.protobuf.json_format import ParseDict
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.project_pb2 import Project as ProjectProto
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.project.adapter import ProjectK8sAdapter


class ProjectK8sAdapterTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.variables = [
            # no-default-value variable
            {
                'name': 'TEST_NO_DEFAULT_VARIABLE',
                'value': 'test'
            },
            # default-value variable
            {
                'name': 'VOLUMES',
                'value': json.dumps([
                    {
                        'hostPath': {
                            'path': '/test'
                        },
                        'name': 'test'
                    }
                ])
            },
            {
                'name': 'VOLUME_MOUNTS',
                'value': json.dumps([
                    {
                        'mountPath': '/test',
                        'name': 'test'
                    }
                ])
            }
        ]
        self.default_project = Project()
        self.default_project.name = 'test-self.default_project'
        self.default_project.set_config(ParseDict({
            'participants': [
                {
                    'name': 'test-participant',
                    'domain_name': 'fl-test.com',
                    'url': '127.0.0.1:32443'
                }
            ],
            'variables': self.variables
        }, ProjectProto()))
        self.default_project.comment = 'test comment'
        db.session.add(self.default_project)
        db.session.commit()
        self.project_k8s_adapter = ProjectK8sAdapter(self.default_project.id)

    def test_exact_variable_from_config(self):
        # no default value
        self.assertEqual('test',
                         self.project_k8s_adapter
                         ._exact_variable_from_config(
                             'TEST_NO_DEFAULT_VARIABLE'))
        # using default value
        self.assertEqual('default',
                         self.project_k8s_adapter
                         ._exact_variable_from_config('NAMESPACE'))
        # using new value
        self.assertEqual(json.dumps([
            {'hostPath': {
                'path': '/test'
            },
                'name': 'test'
            }
        ]), self.project_k8s_adapter._exact_variable_from_config('VOLUMES'))

    def test_get_global_replica_spec(self):
        self.assertEqual({
            'global_replica_spec': {
                'template': {
                    'spec': {
                        'imagePullSecrets': [
                            {
                                'name': 'regcred'
                            }
                        ],
                        'volumes': [
                            {
                                'hostPath': {
                                    'path': '/test'
                                },
                                'name': 'test'
                            }
                        ],
                        'containers': [
                            {
                                'env': self.variables,
                                'volumeMounts': [
                                    {
                                        'mountPath': '/test',
                                        'name': 'test'
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }, self.project_k8s_adapter.get_global_replica_spec())

        if __name__ == '__main__':
            unittest.main()
