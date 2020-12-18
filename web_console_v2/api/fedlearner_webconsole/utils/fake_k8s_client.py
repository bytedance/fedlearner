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
import logging

from fedlearner_webconsole.utils.k8s_client import K8sClient

_RAISE_EXCEPTION_KEY = 'raise_exception'


class FakeK8sClient(K8sClient):
    """A fake k8s client for development.

    With this client we can decouple the dependency of k8s cluster.
    """
    def __init__(self):
        # Do not call super constructor
        pass

    def close(self):
        pass

    def create_secret(self, data: dict, metadata: dict, type: str):
        if _RAISE_EXCEPTION_KEY in data:
            raise RuntimeError('[500] Fake exception for create_secret')
        # Otherwise succeeds
        logging.info('======================')
        logging.info('Created a secret with: data: {}, metadata: {}, type: {}'.format(
            data,
            metadata,
            type
        ))

    def delete_secret(self, name, namespace='default'):
        raise NotImplementedError()

    def get_secret(self, name, namespace='default'):
        raise NotImplementedError()

    def create_service(self, metadata: dict, spec: dict):
        raise NotImplementedError()

    def delete_service(self, name, namespace='default'):
        raise NotImplementedError()

    def get_service(self, name, namespace='default'):
        raise NotImplementedError()

    def create_ingress(self, metadata: dict, spec: dict):
        raise NotImplementedError()

    def delete_ingress(self, name, namespace='default'):
        raise NotImplementedError()

    def get_ingress(self, name, namespace='default'):
        raise NotImplementedError()
