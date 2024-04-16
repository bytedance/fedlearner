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
from envs import Envs

from fedlearner_webconsole.utils.mixins import from_dict_mixin, to_dict_mixin

SPARK_POD_CONFIG_SERILIZE_FIELDS = [
    'cores', 'memory', 'instances', 'core_limit', 'envs', 'volume_mounts'
]


@to_dict_mixin(to_dict_fields=SPARK_POD_CONFIG_SERILIZE_FIELDS,
               ignore_none=True)
@from_dict_mixin(from_dict_fields=SPARK_POD_CONFIG_SERILIZE_FIELDS)
class SparkPodConfig(object):
    def __init__(self):
        self.cores = None
        self.memory = None
        self.instances = None
        self.core_limit = None
        self.volume_mounts = []
        self.envs = {}

    def build_config(self) -> dict:
        """ build config for sparkoperator api
        [ref]: https://github.com/GoogleCloudPlatform/spark-on-k8s-operator

        Returns:
            dict: part of sparkoperator body
        """
        config = {
            'cores': self.cores,
            'memory': self.memory,
        }
        if self.instances:
            config['instances'] = self.instances
        if self.core_limit:
            config['coreLimit'] = self.core_limit
        if self.envs and len(self.envs) > 0:
            config['env'] = [{
                'name': k,
                'value': v
            } for k, v in self.envs.items()]
        if self.volume_mounts and len(self.volume_mounts) > 0:
            config['volumeMounts'] = self.volume_mounts

        return config


SPARK_APP_CONFIG_SERILIZE_FIELDS = [
    'name', 'files', 'files_path', 'volumes', 'image_url', 'driver_config',
    'executor_config', 'command', 'main_application', 'py_files'
]
SPARK_APP_CONFIG_REQUIRED_FIELDS = ['name', 'image_url']


@to_dict_mixin(to_dict_fields=SPARK_APP_CONFIG_SERILIZE_FIELDS,
               ignore_none=True)
@from_dict_mixin(from_dict_fields=SPARK_APP_CONFIG_SERILIZE_FIELDS,
                 required_fields=SPARK_APP_CONFIG_REQUIRED_FIELDS)
class SparkAppConfig(object):
    def __init__(self):
        self.name = None
        # local files should be compressed to submit spark
        self.files = None
        # if nas/hdfs has those files, such as analyzer, only need files path \
        # to submit spark
        self.files_path = None
        self.image_url = None
        self.volumes = []
        self.driver_config = SparkPodConfig()
        self.executor_config = SparkPodConfig()
        self.py_files = []
        self.command = []
        self.main_application = None

    def _replace_placeholder_with_real_path(self, exper: str,
                                            sparkapp_path: str):
        """ replace ${prefix} with real path

        Args:
            sparkapp_path (str): sparkapp real path
        """
        return exper.replace('${prefix}', sparkapp_path)

    def build_config(self, sparkapp_path: str) -> dict:
        return {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'name': self.name,
                'namespace': Envs.K8S_NAMESPACE,
                'labels': Envs.K8S_LABEL_INFO
            },
            'spec': {
                'type':
                'Python',
                'pythonVersion':
                '3',
                'mode':
                'cluster',
                'image':
                self.image_url,
                'imagePullPolicy':
                'Always',
                'volumes':
                self.volumes,
                'mainApplicationFile':
                self._replace_placeholder_with_real_path(
                    self.main_application, sparkapp_path),
                'arguments': [
                    self._replace_placeholder_with_real_path(c, sparkapp_path)
                    for c in self.command
                ],
                'deps': {
                    'pyFiles': [
                        self._replace_placeholder_with_real_path(
                            f, sparkapp_path) for f in self.py_files
                    ]
                },
                'sparkConf': {
                    'spark.shuffle.service.enabled': 'false',
                },
                'sparkVersion':
                '3.0.0',
                'restartPolicy': {
                    'type': 'Never',
                },
                'dynamicAllocation': {
                    'enabled': False,
                },
                'driver': {
                    **self.driver_config.build_config(),
                    'labels': {
                        'version': '3.0.0'
                    },
                    'serviceAccount': 'spark',
                },
                'executor': {
                    **self.executor_config.build_config(),
                    'labels': {
                        'version': '3.0.0'
                    },
                }
            }
        }


SPARK_APP_INFO_SERILIZE_FIELDS = [
    'name', 'namespace', 'command', 'driver', 'executor', 'image_url',
    'main_application', 'spark_version', 'type', 'state'
]


@to_dict_mixin(to_dict_fields=SPARK_APP_INFO_SERILIZE_FIELDS, ignore_none=True)
@from_dict_mixin(from_dict_fields=SPARK_APP_INFO_SERILIZE_FIELDS)
class SparkAppInfo(object):
    @classmethod
    def from_k8s_resp(cls, resp):
        sparkapp_info = cls()
        if 'name' in resp['metadata']:
            sparkapp_info.name = resp['metadata']['name']
        elif 'name' in resp['details']:
            sparkapp_info.name = resp['details']['name']
        sparkapp_info.namespace = resp['metadata'].get('namespace', None)
        sparkapp_info.state = None
        if 'status' in resp:
            if isinstance(resp['status'], str):
                sparkapp_info.state = None
            elif isinstance(resp['status'], dict):
                sparkapp_info.state = resp.get('status',
                                               {}).get('applicationState',
                                                       {}).get('state', None)
        sparkapp_info.command = resp.get('spec', {}).get('arguments', None)
        sparkapp_info.executor = SparkPodConfig.from_dict(
            resp.get('spec', {}).get('executor', {}))
        sparkapp_info.driver = SparkPodConfig.from_dict(
            resp.get('spec', {}).get('driver', {}))
        sparkapp_info.image_url = resp.get('spec', {}).get('image', None)
        sparkapp_info.main_application = resp.get('spec', {}).get(
            'mainApplicationFile', None)
        sparkapp_info.spark_version = resp.get('spec',
                                               {}).get('sparkVersion', None)
        sparkapp_info.type = resp.get('spec', {}).get('type', None)

        return sparkapp_info

    def __init__(self):
        self.name = None
        self.state = None
        self.namespace = None
        self.command = None
        self.driver = SparkPodConfig()
        self.executor = SparkPodConfig()
        self.image_url = None
        self.main_application = None
        self.spark_version = None
        self.type = None
