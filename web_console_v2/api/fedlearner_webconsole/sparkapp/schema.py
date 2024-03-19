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
import base64
import logging
from typing import Optional
from google.protobuf.json_format import ParseDict, MessageToDict
from fedlearner_webconsole.db import db
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.images import generate_unified_version_image
from fedlearner_webconsole.proto import sparkapp_pb2


class SparkPodConfig(object):

    def __init__(self, spark_pod_config: sparkapp_pb2.SparkPodConfig):
        self._spark_pod_config = spark_pod_config

    @classmethod
    def from_dict(cls, inputs: dict) -> 'SparkPodConfig':
        spark_pod_config = sparkapp_pb2.SparkPodConfig()
        envs = inputs.pop('envs')
        inputs['env'] = [{'name': k, 'value': v} for k, v in envs.items()]
        spark_pod_config = ParseDict(inputs, spark_pod_config, ignore_unknown_fields=True)
        return cls(spark_pod_config)

    def build_config(self) -> dict:
        """ build config for sparkoperator api
        [ref]: https://github.com/GoogleCloudPlatform/spark-on-k8s-operator

        Returns:
            dict: part of sparkoperator body
        """
        return MessageToDict(self._spark_pod_config,
                             including_default_value_fields=False,
                             preserving_proto_field_name=False)


class SparkAppConfig(object):

    def __init__(self, spark_app_config: sparkapp_pb2.SparkAppConfig):
        self._spark_app_config = spark_app_config
        self.files: Optional[bytes] = None

    @property
    def files_path(self):
        return self._spark_app_config.files_path

    @property
    def name(self):
        return self._spark_app_config.name

    @classmethod
    def from_dict(cls, inputs: dict) -> 'SparkAppConfig':
        self = cls(sparkapp_pb2.SparkAppConfig())
        if 'files' in inputs:
            input_files = inputs.pop('files')
            if isinstance(input_files, str):
                self.files = base64.b64decode(input_files)
            elif isinstance(input_files, (bytearray, bytes)):
                self.files = input_files
            else:
                logging.debug(f'[SparkAppConfig]: ignore parsing files fields, expected type is str or bytes, \
                        actually is {type(input_files)}')
        self._spark_app_config = ParseDict(inputs, self._spark_app_config, ignore_unknown_fields=True)
        return self

    def _replace_placeholder_with_real_path(self, exper: str, sparkapp_path: str) -> str:
        """ replace ${prefix} with real path

        Args:
            exper (str): sparkapp expression in body
            sparkapp_path (str): sparkapp real path

        Returns:
            return the real path without ${prefix} expression
        """
        return exper.replace('${prefix}', sparkapp_path)

    def build_config(self, sparkapp_path: str) -> dict:
        # sparkapp configuration limitation: initial executors must [5, 30]
        if self._spark_app_config.executor_config.instances > 30:
            self._spark_app_config.dynamic_allocation.max_executors = self._spark_app_config.executor_config.instances
            self._spark_app_config.executor_config.instances = 30

        with db.session_scope() as session:
            setting_service = SettingService(session)
            sys_variables = setting_service.get_system_variables_dict()
            namespace = setting_service.get_namespace()
            labels = sys_variables.get('labels')
            if not self._spark_app_config.image_url:
                self._spark_app_config.image_url = generate_unified_version_image(sys_variables.get('spark_image'))
            for volume in sys_variables.get('volumes_list', []):
                self._spark_app_config.volumes.append(
                    ParseDict(volume, sparkapp_pb2.Volume(), ignore_unknown_fields=True))
            for volume_mount in sys_variables.get('volume_mounts_list', []):
                volume_mount_pb = ParseDict(volume_mount, sparkapp_pb2.VolumeMount(), ignore_unknown_fields=True)
                self._spark_app_config.executor_config.volume_mounts.append(volume_mount_pb)
                self._spark_app_config.driver_config.volume_mounts.append(volume_mount_pb)
            envs_list = []
            for env in sys_variables.get('envs_list', []):
                envs_list.append(ParseDict(env, sparkapp_pb2.Env()))
            self._spark_app_config.driver_config.env.extend(envs_list)
            self._spark_app_config.executor_config.env.extend(envs_list)
            base_config = {
                'apiVersion': 'sparkoperator.k8s.io/v1beta2',
                'kind': 'SparkApplication',
                'metadata': {
                    'name': self._spark_app_config.name,
                    'namespace': namespace,
                    'labels': labels,
                    # Aimed for resource queue management purpose.
                    # It should work fine on where there is no resource queue service.
                    'annotations': {
                        'queue': 'fedlearner-spark',
                        'schedulerName': 'batch',
                    },
                },
                'spec': {
                    'type':
                        'Python',
                    'timeToLiveSeconds':
                        1800,
                    'pythonVersion':
                        '3',
                    'mode':
                        'cluster',
                    'image':
                        self._spark_app_config.image_url,
                    'imagePullPolicy':
                        'IfNotPresent',
                    'volumes': [
                        MessageToDict(volume, including_default_value_fields=False, preserving_proto_field_name=False)
                        for volume in self._spark_app_config.volumes
                    ],
                    'arguments': [
                        self._replace_placeholder_with_real_path(c, sparkapp_path)
                        for c in self._spark_app_config.command
                    ],
                    'sparkConf': {
                        'spark.shuffle.service.enabled': 'false',
                    },
                    'sparkVersion':
                        '3.0.0',
                    'restartPolicy': {
                        'type': 'Never',
                    },
                    'dynamicAllocation':
                        MessageToDict(self._spark_app_config.dynamic_allocation,
                                      including_default_value_fields=False,
                                      preserving_proto_field_name=False),
                    'driver': {
                        **SparkPodConfig(self._spark_app_config.driver_config).build_config(),
                        'labels': {
                            'version': '3.0.0'
                        },
                        'serviceAccount': 'spark',
                    },
                    'executor': {
                        **SparkPodConfig(self._spark_app_config.executor_config).build_config(),
                        'labels': {
                            'version': '3.0.0'
                        },
                    }
                }
            }
            if self._spark_app_config.main_application:
                base_config['spec']['mainApplicationFile'] = self._replace_placeholder_with_real_path(
                    self._spark_app_config.main_application, sparkapp_path)
            if self._spark_app_config.py_files:
                base_config['spec']['deps'] = {
                    'pyFiles': [
                        self._replace_placeholder_with_real_path(f, sparkapp_path)
                        for f in self._spark_app_config.py_files
                    ]
                }
        return base_config


def from_k8s_resp(resp: dict) -> sparkapp_pb2.SparkAppInfo:
    sparkapp_info = sparkapp_pb2.SparkAppInfo()
    if 'name' in resp['metadata']:
        sparkapp_info.name = resp['metadata']['name']
    elif 'name' in resp['details']:
        sparkapp_info.name = resp['details']['name']
    sparkapp_info.namespace = resp['metadata'].get('namespace', '')
    if 'status' in resp:
        if isinstance(resp['status'], str):
            sparkapp_info.state = resp['status']
        elif isinstance(resp['status'], dict):
            sparkapp_info.state = resp.get('status', {}).get('applicationState', {}).get('state', '')
    sparkapp_info.command.extend(resp.get('spec', {}).get('arguments', []))
    sparkapp_info.executor.MergeFrom(
        ParseDict(resp.get('spec', {}).get('executor', {}), sparkapp_pb2.SparkPodConfig(), ignore_unknown_fields=True))
    sparkapp_info.driver.MergeFrom(
        ParseDict(resp.get('spec', {}).get('driver', {}), sparkapp_pb2.SparkPodConfig(), ignore_unknown_fields=True))
    sparkapp_info.image_url = resp.get('spec', {}).get('image', '')
    sparkapp_info.main_application = resp.get('spec', {}).get('mainApplicationFile', '')
    sparkapp_info.spark_version = resp.get('spec', {}).get('sparkVersion', '3')
    sparkapp_info.type = resp.get('spec', {}).get('type', '')

    return sparkapp_info
