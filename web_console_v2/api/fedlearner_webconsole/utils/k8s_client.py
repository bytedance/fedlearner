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
import os
from http import HTTPStatus
from typing import Optional

import kubernetes
import requests
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from fedlearner_webconsole.utils.decorators import retry_fn
from fedlearner_webconsole.utils.fake_k8s_client import FakeK8sClient
from fedlearner_webconsole.utils.k8s_cache import k8s_cache
from envs import Envs


class CrdKind(enum.Enum):
    FLAPP = 'flapps'
    SPARK_APPLICATION = 'sparkapplications'


FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'

SPARKOPERATOR_CUSTOM_GROUP = 'sparkoperator.k8s.io'
SPARKOPERATOR_CUSTOM_VERSION = 'v1beta2'
SPARKOPERATOR_NAMESPACE = 'default'


class K8sClient(object):
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

    def create_or_update_secret(self,
                                data,
                                metadata,
                                secret_type,
                                name,
                                namespace='default'):
        """Create secret. If existed, then replace"""
        request = client.V1Secret(api_version='v1',
                                  data=data,
                                  kind='Secret',
                                  metadata=metadata,
                                  type=secret_type)
        try:
            self.core.read_namespaced_secret(name, namespace)
            # If the secret already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self.core.patch_namespaced_secret(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the secret does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self.core.create_namespaced_secret(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_secret(self, name, namespace='default'):
        try:
            self.core.delete_namespaced_secret(name, namespace)
        except ApiException as e:
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def get_secret(self, name, namespace='default'):
        try:
            return self.core.read_namespaced_secret(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_or_update_service(self,
                                 metadata,
                                 spec,
                                 name,
                                 namespace='default'):
        """Create secret. If existed, then replace"""
        request = client.V1Service(api_version='v1',
                                   kind='Service',
                                   metadata=metadata,
                                   spec=spec)
        try:
            self.core.read_namespaced_service(name, namespace)
            # If the service already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self.core.patch_namespaced_service(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the service does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self.core.create_namespaced_service(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_service(self, name, namespace='default'):
        try:
            self.core.delete_namespaced_service(name, namespace)
        except ApiException as e:
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def get_service(self, name, namespace='default'):
        try:
            return self.core.read_namespaced_service(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_or_update_ingress(self,
                                 metadata,
                                 spec,
                                 name,
                                 namespace='default'):
        request = client.NetworkingV1beta1Ingress(
            api_version='networking.k8s.io/v1beta1',
            kind='Ingress',
            metadata=metadata,
            spec=spec)
        try:
            self._networking.read_namespaced_ingress(name, namespace)
            # If the ingress already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self._networking.patch_namespaced_ingress(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the ingress does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self._networking.create_namespaced_ingress(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_ingress(self, name, namespace='default'):
        try:
            self._networking.delete_namespaced_ingress(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def get_ingress(self, name, namespace='default'):
        try:
            return self._networking.read_namespaced_ingress(name, namespace)
        except ApiException as e:
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def create_or_update_deployment(self,
                                    metadata,
                                    spec,
                                    name,
                                    namespace='default'):
        request = client.V1Deployment(api_version='apps/v1',
                                      kind='Deployment',
                                      metadata=metadata,
                                      spec=spec)
        try:
            self._app.read_namespaced_deployment(name, namespace)
            # If the deployment already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self._app.patch_namespaced_deployment(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the deployment does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self._app.create_namespaced_deployment(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_deployment(self, name, namespace='default'):
        try:
            self._app.delete_namespaced_deployment(name, namespace)
        except ApiException as e:
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def get_deployment(self, name, namespace='default'):
        try:
            return self._app.read_namespaced_deployment(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    @retry_fn(retry_times=3)
    def delete_flapp(self, flapp_name):
        try:
            self.crds.delete_namespaced_custom_object(
                group=FEDLEARNER_CUSTOM_GROUP,
                version=FEDLEARNER_CUSTOM_VERSION,
                namespace=Envs.K8S_NAMESPACE,
                plural=CrdKind.FLAPP.value,
                name=flapp_name)
        except ApiException as e:
            # If the flapp has been deleted then the exception gets ignored
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    @retry_fn(retry_times=3)
    def create_flapp(self, flapp_yaml):
        try:
            self.crds.create_namespaced_custom_object(
                group=FEDLEARNER_CUSTOM_GROUP,
                version=FEDLEARNER_CUSTOM_VERSION,
                namespace=Envs.K8S_NAMESPACE,
                plural=CrdKind.FLAPP.value,
                body=flapp_yaml)
        except ApiException as e:
            # If the flapp exists then we delete it
            if e.status == HTTPStatus.CONFLICT:
                self.delete_flapp(flapp_yaml['metadata']['name'])
            # Raise to make it retry
            raise

    def get_flapp(self, flapp_name):
        return k8s_cache.get_cache(flapp_name)

    def get_webshell_session(self,
                             flapp_name: str,
                             container_name: str,
                             namespace='default'):
        response = requests.get(
            '{api_server_url}/namespaces/{namespace}/pods/{custom_object_name}/'
            'shell/${container_name}'.format(
                api_server_url=self._api_server_url,
                namespace=namespace,
                custom_object_name=flapp_name,
                container_name=container_name))
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError('{}:{}'.format(response.status_code,
                                              response.content))
        return response.json()

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

    def get_pod_log(self, name: str, namespace: str, tail_lines: int):
        try:
            return self.core.read_namespaced_pod_log(name=name,
                                                     namespace=namespace,
                                                     tail_lines=tail_lines)
        except ApiException as e:
            self._raise_runtime_error(e)

    def get_pods(self, namespace, label_selector):
        try:
            return self.core.list_namespaced_pod(namespace=namespace,
                                                 label_selector=label_selector)
        except ApiException as e:
            self._raise_runtime_error(e)


k8s_client = FakeK8sClient()
if Envs.FLASK_ENV == 'production' or \
        Envs.K8S_CONFIG_PATH is not None:
    k8s_client = K8sClient()
    k8s_client.init(Envs.K8S_CONFIG_PATH)
