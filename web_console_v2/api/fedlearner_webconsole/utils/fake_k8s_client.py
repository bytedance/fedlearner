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
# pylint: disable=logging-format-interpolation
import logging
from kubernetes import client
from fedlearner_webconsole.utils.k8s_client import K8sClient

_RAISE_EXCEPTION_KEY = 'raise_exception'


class FakeK8sClient(K8sClient):
    """A fake k8s client for development.

    With this client we can decouple the dependency of k8s cluster.
    """
    def __init__(self):  # pylint: disable=super-init-not-called
        # Do not call super constructor
        pass

    def close(self):
        pass

    def create_or_update_secret(self, data, metadata, secret_type,
                                name, namespace='default'):
        # User may pass two type of data:
        # 1. dictionary
        # 2. K8s Object
        # They are both accepted by real K8s client,
        # but K8s Object is not iterable.
        if isinstance(data, dict) and _RAISE_EXCEPTION_KEY in data:
            raise RuntimeError('[500] Fake exception for save_secret')
        # Otherwise succeeds
        logging.info('======================')
        logging.info('Saved a secret with: data: {}, '
                     'metadata: {}, type: {}'.format(
            data,
            metadata,
            secret_type
        ))

    def delete_secret(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a secret with: name: {}'.format(
            name
        ))

    def get_secret(self, name, namespace='default'):
        return client.V1Secret(api_version='v1',
                               data={'test': 'test'},
                               kind='Secret',
                               metadata={'name': name, 'namespace': namespace},
                               type='Opaque')

    def create_or_update_service(self, metadata, spec, name,
                                 namespace='default'):
        logging.info('======================')
        logging.info('Saved a service with: spec: {}, metadata: {}'.format(
            spec,
            metadata
        ))

    def delete_service(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a service with: name: {}'.format(
            name
        ))

    def get_service(self, name, namespace='default'):
        return client.V1Service(api_version='v1',
                                kind='Service',
                                metadata=client.V1ObjectMeta(
                                    name=name,
                                    namespace=namespace
                                ),
                                spec=client.V1ServiceSpec(
                                    selector={'app': 'nginx'}
                                ))

    def create_or_update_ingress(self, metadata, spec, name,
                                 namespace='default'):
        logging.info('======================')
        logging.info('Saved a ingress with: spec: {}, metadata: {}'.format(
            spec,
            metadata
        ))

    def delete_ingress(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a ingress with: name: {}'.format(
            name
        ))

    def get_ingress(self, name, namespace='default'):
        return client.NetworkingV1beta1Ingress(
            api_version='networking.k8s.io/v1beta1',
            kind='Ingress',
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace
            ),
            spec=client.NetworkingV1beta1IngressSpec()
        )

    def create_or_update_deployment(self, metadata, spec, name,
                                    namespace='default'):
        logging.info('======================')
        logging.info('Saved a deployment with: spec: {}, metadata: {}'.format(
            spec,
            metadata
        ))

    def delete_deployment(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a deployment with: name: {}'.format(
            name
        ))

    def get_deployment(self, name, namespace='default'):
        return client.V1Deployment(
            api_version='apps/v1',
            kind='Deployment',
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1DeploymentSpec(
                selector={'matchLabels': {'app': 'fedlearner-operator'}},
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name='fedlearner-operator',
                                args=[
                                    'test'
                                ]
                            )
                        ]
                    )
                )
            )
        )

    def getWebshellSession(self, namespace, pod_name, mode):
        logging.info('======================')
        logging.info('get container from pod : {}'.format(
            pod_name
        ))
        return 'A container Id'

    def get_flapp(self, namespace, job_name):
        logging.info('======================')
        logging.info('get detail from job : {}'.format(
            job_name
        ))
        return {'name':job_name}

    def get_pods(self, namespace, job_name):
        logging.info('======================')
        logging.info('get pods from job : {}'.format(
            job_name
        ))
        return {'name': job_name}

    def createFLApp(self, namespace, yaml):
        logging.info('======================')
        logging.info('create flapp from yaml : {}'.format(
            yaml
        ))

    def deleteFLApp(self, namespace, job_name):
        logging.info('======================')
        logging.info('delete flapp: {}'.format(
            job_name
        ))

    def getBaseUrl(self):
        return "fake/url"
