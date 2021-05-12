# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import enum
import logging
import os
from http import HTTPStatus
from typing import Optional
import subprocess

import kubernetes
import requests
from kubernetes import client
from kubernetes.client.exceptions import ApiException


class CrdKind(enum.Enum):
    FLAPP = 'flapps'
    SPARK_APPLICATION = 'sparkapplications'


FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'

SPARKOPERATOR_CUSTOM_GROUP = 'sparkoperator.k8s.io'
SPARKOPERATOR_CUSTOM_VERSION = 'v1beta2'
SPARKOPERATOR_NAMESPACE = 'default'


class K8SClient(object):
    def __init__(self):
        self.core = None
        self.crds = None
        self._networking = None
        self._app = None
        self._api_server_url = 'http://{}:{}'.format(
            os.environ.get('FL_API_SERVER_HOST', 'fedlearner-apiserver'),
            os.environ.get('FL_API_SERVER_PORT', 8101))

    def init(self, config_path: Optional[str] = None):
        # Sets config
        if config_path is None:
            kubernetes.config.load_incluster_config()
        else:
            kubernetes.config.load_kube_config(config_path)
        # Inits API clients
        self.core = client.CoreV1Api()
        self.crds = client.CustomObjectsApi()
        self._networking = client.NetworkingV1beta1Api()
        self._app = client.AppsV1Api()

    def close(self):
        self.core.api_client.close()
        self._networking.api_client.close()

    def _raise_runtime_error(self, exception: ApiException):
        raise RuntimeError('[{}] {}'.format(exception.status,
                                            exception.reason))

    def get_sparkapplication(self,
                             name: str,
                             namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        try:
            return self.crds.get_namespaced_custom_object(
                group=SPARKOPERATOR_CUSTOM_GROUP,
                version=SPARKOPERATOR_CUSTOM_VERSION,
                namespace=namespace,
                plural=CrdKind.SPARK_APPLICATION.value,
                name=name)
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_sparkapplication(
            self,
            json_object: dict,
            namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        try:
            return self.crds.create_namespaced_custom_object(
                group=SPARKOPERATOR_CUSTOM_GROUP,
                version=SPARKOPERATOR_CUSTOM_VERSION,
                namespace=namespace,
                plural=CrdKind.SPARK_APPLICATION.value,
                body=json_object)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_sparkapplication(self,
                                name: str,
                                namespace: str = SPARKOPERATOR_NAMESPACE
                                ) -> dict:
        try:
            return self.crds.delete_namespaced_custom_object(
                group=SPARKOPERATOR_CUSTOM_GROUP,
                version=SPARKOPERATOR_CUSTOM_VERSION,
                namespace=namespace,
                plural=CrdKind.SPARK_APPLICATION.value,
                name=name,
                body=client.V1DeleteOptions())
        except ApiException as e:
            self._raise_runtime_error(e)


class FakeK8SClient(object):
    def __init__(self, cmd: str, args: list = None):
        self._cmd = cmd
        self._args = args
        self._process = None

    def close(self):
        pass

    def _raise_runtime_error(self, exception: ApiException):
        raise RuntimeError('[{}] {}'.format(exception.status,
                                            exception.reason))

    def get_sparkapplication(self,
                             name: str,
                             namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        stdout_data, stderr_data = self._process.communicate()
        logging.info(stdout_data.decode('utf-8'))
        res = {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp': '2021-04-15T10:43:15Z',
                'generation': 1,
                'name': name,
                'namespace': namespace,
            },
            'status': {
                'applicationState': {
                    'state': ''
                },
            }
        }
        if self._process.returncode is None:
            res['status']['applicationState']['state'] = "RUNNING"
        elif self._process.returncode == 0:
            res['status']['applicationState']['state'] = "COMPLETED"
        else:
            res['status']['applicationState']['state'] = "FAILED"
        return res

    def create_sparkapplication(
        self,
        json_object: dict,
        namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:

        cmd = ['python', self._cmd] + self._args
        logging.info(cmd)
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
        return {
            "name": "fake_spark_app"
        }

    def delete_sparkapplication(self,
                                name: str,
                                namespace: str = SPARKOPERATOR_NAMESPACE
                                ) -> dict:
        try:
            return self.crds.delete_namespaced_custom_object(
                group=SPARKOPERATOR_CUSTOM_GROUP,
                version=SPARKOPERATOR_CUSTOM_VERSION,
                namespace=namespace,
                plural=CrdKind.SPARK_APPLICATION.value,
                name=name,
                body=client.V1DeleteOptions())
        except ApiException as e:
            self._raise_runtime_error(e)

