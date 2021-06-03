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
from typing import Optional
import subprocess

import kubernetes
from kubernetes import client
from kubernetes.client.exceptions import ApiException


class CrdKind(enum.Enum):
    SPARK_APPLICATION = 'sparkapplications'


FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'

SPARKOPERATOR_CUSTOM_GROUP = 'sparkoperator.k8s.io'
SPARKOPERATOR_CUSTOM_VERSION = 'v1beta2'
SPARKOPERATOR_NAMESPACE = 'default'


class K8SAPPStatus(enum.Enum):
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FAILING = "FAILING"


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
        if not config_path:
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
        raise RuntimeError('Body {}, [{}] {}'.format(
            exception.body, exception.status, exception.reason))

    def get_sparkapplication(self,
                             name: str,
                             namespace: str = SPARKOPERATOR_NAMESPACE) \
            -> (K8SAPPStatus, str):
        try:
            resp = self.crds.get_namespaced_custom_object_status(
                group=SPARKOPERATOR_CUSTOM_GROUP,
                version=SPARKOPERATOR_CUSTOM_VERSION,
                namespace=namespace,
                plural=CrdKind.SPARK_APPLICATION.value,
                name=name)
            if 'status' in resp and \
                resp['status']['applicationState']['state'] in K8SAPPStatus:
                return (
                    K8SAPPStatus[resp['status']['applicationState']['state']],
                    resp)
            return K8SAPPStatus.PENDING, ''
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_sparkapplication(
            self,
            body,
            namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        try:
            return self.crds.create_namespaced_custom_object(
                group=SPARKOPERATOR_CUSTOM_GROUP,
                version=SPARKOPERATOR_CUSTOM_VERSION,
                namespace=namespace,
                plural=CrdKind.SPARK_APPLICATION.value,
                body=body)
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
    def __init__(self):
        self._process = None

    @staticmethod
    def name_key():
        return "name"

    @staticmethod
    def entry_key():
        return "entry"

    @staticmethod
    def arg_key():
        return "args"

    def close(self):
        pass

    def _raise_runtime_error(self, exception: ApiException):
        raise RuntimeError('[{}] {}'.format(exception.status,
                                            exception.reason))

    def get_sparkapplication(self,
                             name: str,
                             namespace: str = SPARKOPERATOR_NAMESPACE)\
            -> (K8SAPPStatus, str):
        stdout_data, stderr_data = self._process.communicate()
        logging.info(stdout_data.decode('utf-8'))
        if not self._process:
            self._raise_runtime_error(
                ApiException("Task {} not exist".format(name)))
        elif self._process.returncode is None:
            return K8SAPPStatus.RUNNING, ''
        elif self._process.returncode == 0:
            return K8SAPPStatus.COMPLETED, ''
        return K8SAPPStatus.FAILED, 'Failed'

    def create_sparkapplication(
        self,
        body,
        namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:

        entry_script = body[self.entry_key()]
        args = body[self.arg_key()]
        cmd = ['python', entry_script] + args
        logging.info(cmd)
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp': '2021-05-13T08:41:48Z',
                'generation': 1,
                'name': body[self.name_key()],
                'namespace': namespace,
                'resourceVersion': '2894990020',
                'selfLink': '/apis/sparkoperator.k8s.io/v1beta2/namespaces',
                'uid': "123-ds3"
            }
        }

    def delete_sparkapplication(self,
                                name: str,
                                namespace: str = SPARKOPERATOR_NAMESPACE
                                ) -> dict:
        logging.info("Delete spark application %s in namespace %s", name,
                     namespace)
        return {}
