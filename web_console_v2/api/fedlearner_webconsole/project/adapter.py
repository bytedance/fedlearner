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
import json

DEFAULT_VALUE = {
    'NAMESPACE': 'default',
    'STORAGE_ROOT_PATH': '/data',
    'CLEAN_POD_POLICY': 'All',
    'VOLUMES': '[]',
    'VOLUME_MOUNTS': '[]',
    'EGRESS_URL': 'fedlearner-stack-ingress-nginx-controller.'
                  'default.svc.cluster.local:80',
    'WEB_CONSOLE_URL': 'default.fedlearner.webconsole',
    'OPERATOR_URL': 'default.fedlearner.operator'
}


class ProjectK8sAdapter:
    """Project Adapter for getting K8s settings"""
    def __init__(self, project):
        self._project = project
        self._variables = {
            var.name: var.value
            for var in project.get_config().variables
        }

    def get_namespace(self):
        return self._exact_variable('NAMESPACE')

    def get_storage_root_path(self):
        return self._exact_variable('STORAGE_ROOT_PATH')

    def get_global_job_spec(self):
        return {
            'global_job_spec': {
                'spec': {
                    'cleanPodPolicy':
                        self._exact_variable('CLEAN_POD_POLICY')
                }
            }
        }

    def get_global_replica_spec(self):
        variable_list = [
            {'name': key, 'value': value}
            for key, value in self._variables.items()
        ]
        return {
            'global_replica_spec': {
                'template': {
                    'spec': {
                        'imagePullSecrets': [
                            {
                                'name': 'regcred'
                            }
                        ],
                        'volumes': json.loads(
                            self._exact_variable('VOLUMES')),
                        'containers': [
                            {
                                'env': variable_list,
                                'volumeMounts':
                                    json.loads(self._exact_variable(
                                        'VOLUME_MOUNTS'))
                            }
                        ]
                    }
                }
            }
        }

    def get_web_console_grpc_spec(self):
        return {
            participant.domain_name: {
                'peerUrl': self._exact_variable('EGRESS_URL'),
                'authority': participant.domain_name,
                'extraHeaders': {
                    'x-host': self._exact_variable(
                        'WEB_CONSOLE_URL')
                }
            } for participant in self._project.get_participants()
        }

    def get_worker_grpc_spec(self):
        return {
            participant.domain_name: {
                'peerUrl': self._exact_variable('EGRESS_URL'),
                'authority': participant.domain_name,
                'extraHeaders': {
                    'x-host': self._exact_variable(
                        'OPERATOR_URL')
                }
            } for participant in self._project.get_participants()
        }

    def _exact_variable(self, variable_name):
        if variable_name in self._variables:
            return self._variables[variable_name]
        return DEFAULT_VALUE.get(variable_name)
