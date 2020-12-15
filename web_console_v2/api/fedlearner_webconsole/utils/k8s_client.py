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

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


class K8sClient(object):

    def __init__(self, config_path=None):
        if config_path is None:
            config.load_incluster_config()
        else:
            config.load_kube_config(config_path)
        self._core = client.CoreV1Api()
        self._networking = client.NetworkingV1beta1Api()

    def close(self):
        self._core.api_client.close()
        self._networking.api_client.close()

    def _raise_runtime_error(self, exception: ApiException):
        raise RuntimeError('[{}] {}'.format(exception.status, exception.reason))

    def save_secret(self, data: dict, metadata: dict, type: str, name, namespace='default'):
        """Create secret. If existed, then replace"""
        request = client.V1Secret(api_version='v1',
                                  data=data,
                                  kind='Secret',
                                  metadata=metadata,
                                  type=type)
        try:
            self._core.create_namespaced_secret(namespace=metadata.get('namespace', 'default'),
                                                body=request)
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

    def create_service(self, metadata: dict, spec: dict):
        request = client.V1Service(api_version='v1',
                                   kind='Service',
                                   metadata=metadata,
                                   spec=spec)
        try:
            self._core.create_namespaced_service(namespace='default',
                                                 body=request)
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

    def create_ingress(self, metadata: dict, spec: dict):
        request = client.NetworkingV1beta1Ingress(
            api_version='networking.k8s.io/v1beta1',
            kind='Ingress',
            metadata=metadata,
            spec=spec
        )
        try:
            self._networking.create_namespaced_ingress(namespace='default',
                                                       body=request)
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
