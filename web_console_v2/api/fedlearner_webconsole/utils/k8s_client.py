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

import os
from http import HTTPStatus
import enum

import requests

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'


class CrdKind(enum.Enum):
    FLAPP = 'flapps'
    SPARK_APPLICATION = 'sparkapplications'


class K8sClient(object):
    def __init__(self, config_path=None):
        if config_path is None:
            config.load_incluster_config()
        else:
            config.load_kube_config(config_path)
        self._core = client.CoreV1Api()
        self._networking = client.NetworkingV1beta1Api()
        self._app = client.AppsV1Api()
        self._custom_object = client.CustomObjectsApi()
        self._client = client.ApiClient()
        self._api_server_url = 'http://{}:{}'.format(
            os.environ.get('FL_API_SERVER_HOST', 'fedlearner-apiserver'),
            os.environ.get('FL_API_SERVER_PORT', 8101))

    def close(self):
        self._core.api_client.close()
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
            self._core.read_namespaced_secret(name, namespace)
            # If the secret already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self._core.patch_namespaced_secret(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the secret does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self._core.create_namespaced_secret(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_secret(self, name, namespace='default'):
        try:
            self._core.delete_namespaced_secret(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def get_secret(self, name, namespace='default'):
        try:
            return self._core.read_namespaced_secret(name, namespace)
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
            self._core.read_namespaced_service(name, namespace)
            # If the service already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self._core.patch_namespaced_service(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the service does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self._core.create_namespaced_service(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_service(self, name, namespace='default'):
        try:
            self._core.delete_namespaced_service(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def get_service(self, name, namespace='default'):
        try:
            return self._core.read_namespaced_service(name, namespace)
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
            self._raise_runtime_error(e)

    def get_deployment(self, name, namespace='default'):
        try:
            return self._app.read_namespaced_deployment(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def get_custom_object(self, kind: CrdKind,
                          custom_object_name: str, namespace='default'):
        try:
            response = self._custom_object.get_namespaced_custom_object(
                group=FEDLEARNER_CUSTOM_GROUP,
                version=FEDLEARNER_CUSTOM_VERSION, namespace=namespace,
                plural=kind.value,
                name=custom_object_name
            )
            return response
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_custom_object(self, kind: CrdKind,
                             custom_object_name: str, namespace='default'):
        try:
            response = self._custom_object.delete_namespaced_custom_object(
                group=FEDLEARNER_CUSTOM_GROUP,
                version=FEDLEARNER_CUSTOM_VERSION, namespace=namespace,
                plural=kind.value,
                name=custom_object_name
            )
            return response
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_custom_object(self, crd_kind: CrdKind, json_object,
                             namespace='default'):
        response = requests.post(
            '{api_server_url}/namespaces/{namespace}/fedlearner/'
            'v1alpha1/{crd_kind}'.format(
                api_server_url=self._api_server_url,
                namespace=namespace,
                crd_kind=crd_kind.value),
            json=json_object)
        if response.status_code != HTTPStatus.CREATED:
            raise RuntimeError('{}:{}'.format(response.status_code,
                                              response.reason))
        return response.json()

    def list_resource_of_custom_object(self, kind: CrdKind,
                                       custom_object_name: str,
                                       resource_type: str, namespace='default'):
        response = requests.get(
            '{api_server_url}/namespaces/{namespace}/fedlearner/v1alpha1/'
            '{plural}/{name}/{resource_type}'.format(
                api_server_url=self._api_server_url,
                namespace=namespace,
                plural=kind.value,
                name=custom_object_name,
                resource_type=resource_type))
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError('{}:{}'.format(response.status_code,
                                              response.reason))
        return response.json()

    def get_webshell_session(self, flapp_name: str,
                             container_name: str, namespace='default'):
        response = requests.get(
            '{api_server_url}/namespaces/{namespace}/pods/{custom_object_name}/'
            'shell/${container_name}'.format(
                api_server_url=self._api_server_url,
                namespace=namespace,
                custom_object_name=flapp_name,
                container_name=container_name))
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError('{}:{}'.format(response.status_code,
                                              response.reason))
        return response.json()
