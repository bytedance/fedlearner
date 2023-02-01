# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
# pylint: disable=inconsistent-return-statements
import enum
import logging
from http import HTTPStatus
from typing import Callable, Optional

import kubernetes
from kubernetes import client
from kubernetes.client import V1ServiceList, NetworkingV1beta1IngressList
from kubernetes.client.exceptions import ApiException

from envs import Envs
from fedlearner_webconsole.utils.decorators.retry import retry_fn
from fedlearner_webconsole.exceptions import (NotFoundException, InternalException)
from fedlearner_webconsole.k8s.fake_k8s_client import FakeK8sClient
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.utils.hooks import parse_and_get_fn

# This is the default k8s client hook.
# Args:
#     app_yaml [dict] the app yaml definition of k8s resource.
# Returns:
#     [dict] the modified app yaml of k8s resource.
# Note:
#     If you want to custom k8s client hook,
#        1. write the hook function according this interface
#        2. assign module_fn to `K8S_HOOK_MODULE_PATH` variables.
DEFAULT_K8S_CLIENT_HOOK: Callable[[dict], dict] = lambda o: o


# TODO(xiangyuxuan.prs): they are just used in dataset, should be deprecated.
class CrdKind(enum.Enum):
    FLAPP = 'flapps'
    SPARK_APPLICATION = 'sparkapplications'


FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'

SPARKOPERATOR_CUSTOM_GROUP = 'sparkoperator.k8s.io'
SPARKOPERATOR_CUSTOM_VERSION = 'v1beta2'
SPARKOPERATOR_NAMESPACE = Envs.K8S_NAMESPACE

REQUEST_TIMEOUT_IN_SECOND = 10


# TODO(wangsen.0914): remove create_deployment etc.; add UT for client
class K8sClient(object):

    def __init__(self):
        self.core = None
        self.crds = None
        self._networking = None
        self._app = None
        self._hook_fn = DEFAULT_K8S_CLIENT_HOOK

    def init(self, config_path: Optional[str] = None, hook_module_path: Optional[str] = None):
        # Sets config
        if config_path is None:
            kubernetes.config.load_incluster_config()
        else:
            kubernetes.config.load_kube_config(config_path)

        # Initialize hook
        if hook_module_path:
            self._hook_fn = parse_and_get_fn(hook_module_path)

        # Inits API clients
        self.core = client.CoreV1Api()
        self.crds = client.CustomObjectsApi()
        self._networking = client.NetworkingV1beta1Api()
        self._app = client.AppsV1Api()

    def close(self):
        self.core.api_client.close()
        self._networking.api_client.close()

    def _raise_runtime_error(self, exception: ApiException):
        logging.error(f'[k8s_client]: runtime error {exception}')
        raise RuntimeError(str(exception))

    def create_or_update_secret(self, data, metadata, secret_type, name, namespace='default'):
        """Create secret. If existed, then replace"""
        request = client.V1Secret(api_version='v1', data=data, kind='Secret', metadata=metadata, type=secret_type)
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

    def create_or_update_config_map(self, metadata, data, name, namespace='default'):
        """Create configMap. If existed, then patch"""
        request = client.V1ConfigMap(api_version='v1', kind='ConfigMap', metadata=metadata, data=data)
        try:
            self.core.read_namespaced_config_map(name, namespace)
            # If the configMap already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self.core.patch_namespaced_config_map(name, namespace, request)
            return
        except ApiException as e:
            # 404 is expected if the configMap does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self.core.create_namespaced_config_map(namespace, request)
        except ApiException as e:
            self._raise_runtime_error(e)

    def delete_config_map(self, name, namespace='default'):
        try:
            self.core.delete_namespaced_config_map(name, namespace)
        except ApiException as e:
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def get_config_map(self, name, namespace='default'):
        try:
            return self.core.read_namespaced_config_map(name, namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_or_update_service(self, metadata, spec, name, namespace='default'):
        """Create secret. If existed, then replace"""
        request = client.V1Service(api_version='v1', kind='Service', metadata=metadata, spec=spec)
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

    def list_service(self, namespace: str = 'default') -> V1ServiceList:
        try:
            return self.core.list_namespaced_service(namespace)
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_or_update_ingress(self, metadata, spec, name, namespace='default'):
        request = client.NetworkingV1beta1Ingress(api_version='networking.k8s.io/v1beta1',
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

    def list_ingress(self, namespace: str = 'default') -> NetworkingV1beta1IngressList:
        try:
            return self._networking.list_namespaced_ingress(namespace)
        except ApiException as e:
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def create_or_update_deployment(self, metadata, spec, name, namespace='default'):
        request = client.V1Deployment(api_version='apps/v1', kind='Deployment', metadata=metadata, spec=spec)
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

    def get_deployment(self, name):
        try:
            return self._app.read_namespaced_deployment(name, Envs.K8S_NAMESPACE)
        except ApiException as e:
            self._raise_runtime_error(e)

    def get_sparkapplication(self, name: str, namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        """get sparkapp

        Args:
            name (str): sparkapp name
            namespace (str, optional): namespace to submit.

        Raises:
            InternalException: if any error occurs during API call
            NotFoundException: if the spark app is not found

        Returns:
            dict: resp of k8s
        """
        try:
            return self.crds.get_namespaced_custom_object(group=SPARKOPERATOR_CUSTOM_GROUP,
                                                          version=SPARKOPERATOR_CUSTOM_VERSION,
                                                          namespace=namespace,
                                                          plural=CrdKind.SPARK_APPLICATION.value,
                                                          name=name)
        except ApiException as err:
            if err.status == 404:
                raise NotFoundException() from err
            raise InternalException(details=err.body) from err

    def create_sparkapplication(self, json_object: dict, namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        """ create sparkapp

        Args:
            json_object (dict): json object of config
            namespace (str, optional): namespace to submit.

        Returns:
            dict: resp of k8s
        """
        logging.debug(f'create sparkapp json is {json_object}')
        return self.crds.create_namespaced_custom_object(group=SPARKOPERATOR_CUSTOM_GROUP,
                                                         version=SPARKOPERATOR_CUSTOM_VERSION,
                                                         namespace=namespace,
                                                         plural=CrdKind.SPARK_APPLICATION.value,
                                                         body=json_object)

    def delete_sparkapplication(self, name: str, namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        """ delete sparkapp

        Args:
            name (str): sparkapp name
            namespace (str, optional): namespace to delete.

        Raises:
            NotFoundException: if the spark app is nout found
            InternalException: if any error occurs during API call

        Returns:
            dict: resp of k8s
        """
        try:
            return self.crds.delete_namespaced_custom_object(group=SPARKOPERATOR_CUSTOM_GROUP,
                                                             version=SPARKOPERATOR_CUSTOM_VERSION,
                                                             namespace=namespace,
                                                             plural=CrdKind.SPARK_APPLICATION.value,
                                                             name=name,
                                                             body=client.V1DeleteOptions())
        except ApiException as err:
            if err.status == 404:
                raise NotFoundException() from err
            raise InternalException(details=err.body) from err

    def get_pod_log(self, name: str, namespace: str, tail_lines: int):
        # this is not necessary for now
        del namespace
        return es.query_log(Envs.ES_INDEX, '', name)[:tail_lines][::-1]

    def get_pods(self, namespace, label_selector):
        try:
            return self.core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        except ApiException as e:
            self._raise_runtime_error(e)

    def create_app(self,
                   app_yaml: dict,
                   group: str,
                   version: str,
                   plural: str,
                   namespace: str = Envs.K8S_NAMESPACE) -> dict:
        try:
            app_yaml = self._hook_fn(app_yaml)
            return self.crds.create_namespaced_custom_object(group=group,
                                                             version=version,
                                                             namespace=namespace,
                                                             plural=plural,
                                                             body=app_yaml,
                                                             _request_timeout=REQUEST_TIMEOUT_IN_SECOND)
        except ApiException as e:
            # 404 is expected if the custom resource does not exist
            if e.status != HTTPStatus.CONFLICT:
                self._raise_runtime_error(e)
            logging.warning(f'Crd object: {app_yaml} has been created!')

    @retry_fn(retry_times=3)
    def delete_app(self, app_name, group, version: str, plural: str, namespace: str = Envs.K8S_NAMESPACE):
        try:
            self.crds.delete_namespaced_custom_object(group=group,
                                                      version=version,
                                                      namespace=namespace,
                                                      plural=plural,
                                                      name=app_name,
                                                      _request_timeout=REQUEST_TIMEOUT_IN_SECOND)
        except ApiException as e:
            # If the custom resource has been deleted then the exception gets ignored
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)

    def get_custom_object(self,
                          name: str,
                          group: str,
                          version: str,
                          plural: str,
                          namespace: str = Envs.K8S_NAMESPACE) -> dict:
        try:
            return self.crds.get_namespaced_custom_object(group=group,
                                                          version=version,
                                                          namespace=namespace,
                                                          plural=plural,
                                                          name=name,
                                                          _request_timeout=REQUEST_TIMEOUT_IN_SECOND)
        except ApiException as e:
            self._raise_runtime_error(e)

    def update_app(self, app_yaml: dict, group: str, version: str, plural: str, namespace: str = Envs.K8S_NAMESPACE):
        try:
            app_yaml = self._hook_fn(app_yaml)
            name = app_yaml['metadata']['name']
            self.crds.patch_namespaced_custom_object(group=group,
                                                     version=version,
                                                     namespace=namespace,
                                                     plural=plural,
                                                     name=name,
                                                     body=app_yaml,
                                                     _request_timeout=REQUEST_TIMEOUT_IN_SECOND)
        except ApiException as e:
            if e.status == HTTPStatus.NOT_FOUND:
                logging.error(f'[k8s_client] Resource: {app_yaml} doesn\'t exist!')
            self._raise_runtime_error(e)

    def create_or_update_app(self,
                             app_yaml: dict,
                             group: str,
                             version: str,
                             plural: str,
                             namespace: str = Envs.K8S_NAMESPACE):
        name = app_yaml['metadata']['name']
        try:
            # Why not use `get_custom_object`?
            # Because `get_custom_object` wraps the exception, it's difficult to parse 404 info.
            self.crds.get_namespaced_custom_object(group=group,
                                                   version=version,
                                                   namespace=namespace,
                                                   plural=plural,
                                                   name=name,
                                                   _request_timeout=REQUEST_TIMEOUT_IN_SECOND)
            # If the resource already exists, then we use patch to replace it.
            # We don't use replace method because it requires `resourceVersion`.
            self.update_app(app_yaml=app_yaml, group=group, version=version, plural=plural, namespace=namespace)
            return
        except ApiException as e:
            # 404 is expected if the deployment does not exist
            if e.status != HTTPStatus.NOT_FOUND:
                self._raise_runtime_error(e)
        try:
            self.create_app(app_yaml=app_yaml, group=group, version=version, plural=plural, namespace=namespace)
        except ApiException as e:
            self._raise_runtime_error(e)


k8s_client = FakeK8sClient()
if Envs.FLASK_ENV == 'production' or \
        Envs.K8S_CONFIG_PATH is not None:
    k8s_client = K8sClient()
    k8s_client.init(config_path=Envs.K8S_CONFIG_PATH, hook_module_path=Envs.K8S_HOOK_MODULE_PATH)
