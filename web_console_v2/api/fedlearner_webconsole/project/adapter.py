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
from fedlearner_webconsole.project.models import Project

DEFAULT_VALUE = {
    'NAMESPACE': 'default',
    'STORAGE_ROOT_PATH': '/',
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
    def __init__(self, project_id):
        self.project = Project.query.filter_by(id=project_id).first()
        if self.project is None:
            raise RuntimeError('No such project')
        self._config = self.project.to_dict().get('config')

    def get_namespace(self):
        return self._exact_variable_from_config('NAMESPACE')

    def get_storage_root_path(self):
        return self._exact_variable_from_config('STORAGE_ROOT_PATH')

    def get_global_job_spec(self):
        return {
            'global_job_spec': {
                'spec': {
                    'cleanPodPolicy':
                        self._exact_variable_from_config('CLEAN_POD_POLICY')
                }
            }
        }

    def get_global_replica_spec(self):
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
                            self._exact_variable_from_config('VOLUMES')),
                        'containers': [
                            {
                                'env': self._config.get('variables'),
                                'volumeMounts':
                                    json.loads(self._exact_variable_from_config(
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
                'peerUrl': self._exact_variable_from_config('EGRESS_URL'),
                'authority': participant.domain_name,
                'extraHeaders': {
                    'x-host': self._exact_variable_from_config(
                        'WEB_CONSOLE_URL')
                }
            } for participant in self.project.get_participants()
        }

    def get_worker_grpc_spec(self):
        return {
            participant.domain_name: {
                'peerUrl': self._exact_variable_from_config('EGRESS_URL'),
                'authority': participant.domain_name,
                'extraHeaders': {
                    'x-host': self._exact_variable_from_config(
                        'OPERATOR_URL')
                }
            } for participant in self.project.get_participants()
        }

    def _exact_variable_from_config(self, variable_name):
        for variable in self._config.get('variables'):
            if variable.get('name') == variable_name:
                return variable.get('value')
        return DEFAULT_VALUE.get(variable_name)
