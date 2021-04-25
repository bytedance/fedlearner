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
from fedlearner_webconsole.utils.k8s_client import K8sClient, \
    SPARKOPERATOR_NAMESPACE

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

    def create_or_update_secret(self,
                                data,
                                metadata,
                                secret_type,
                                name,
                                namespace='default'):
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
                     'metadata: {}, type: {}'.format(data, metadata,
                                                     secret_type))

    def delete_secret(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a secret with: name: {}'.format(name))

    def get_secret(self, name, namespace='default'):
        return client.V1Secret(api_version='v1',
                               data={'test': 'test'},
                               kind='Secret',
                               metadata={
                                   'name': name,
                                   'namespace': namespace
                               },
                               type='Opaque')

    def create_or_update_service(self,
                                 metadata,
                                 spec,
                                 name,
                                 namespace='default'):
        logging.info('======================')
        logging.info('Saved a service with: spec: {}, metadata: {}'.format(
            spec, metadata))

    def delete_service(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a service with: name: {}'.format(name))

    def get_service(self, name, namespace='default'):
        return client.V1Service(
            api_version='v1',
            kind='Service',
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1ServiceSpec(selector={'app': 'nginx'}))

    def create_or_update_ingress(self,
                                 metadata,
                                 spec,
                                 name,
                                 namespace='default'):
        logging.info('======================')
        logging.info('Saved a ingress with: spec: {}, metadata: {}'.format(
            spec, metadata))

    def delete_ingress(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a ingress with: name: {}'.format(name))

    def get_ingress(self, name, namespace='default'):
        return client.NetworkingV1beta1Ingress(
            api_version='networking.k8s.io/v1beta1',
            kind='Ingress',
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.NetworkingV1beta1IngressSpec())

    def create_or_update_deployment(self,
                                    metadata,
                                    spec,
                                    name,
                                    namespace='default'):
        logging.info('======================')
        logging.info('Saved a deployment with: spec: {}, metadata: {}'.format(
            spec, metadata))

    def delete_deployment(self, name, namespace='default'):
        logging.info('======================')
        logging.info('Deleted a deployment with: name: {}'.format(name))

    def get_deployment(self, name, namespace='default'):
        return client.V1Deployment(
            api_version='apps/v1',
            kind='Deployment',
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1DeploymentSpec(
                selector={'matchLabels': {
                    'app': 'fedlearner-operator'
                }},
                template=client.V1PodTemplateSpec(spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(name='fedlearner-operator',
                                           args=['test'])
                    ]))))

    def get_custom_object(self,
                          crd_kind,
                          custom_object_name: str,
                          namespace='default'):
        result = {
            'kind': crd_kind.value,
            'metadata': {
                'name': custom_object_name,
                'namesapce': namespace
            },
            'status': {
                'appState': 'FLStateRunning',
                'flReplicaStatus': {
                    'Master': {
                        'active': {
                            'laomiao-raw-data-1223-v1-follower'
                            '-master-0-717b53c4-'
                            'fef7-4d65-a309-63cf62494286': {}
                        }
                    },
                    'Worker': {
                        'active': {
                            'laomiao-raw-data-1223-v1-follower'
                            '-worker-0-61e49961-'
                            'e6dd-4015-a246-b6d25e69a61c': {},
                            'laomiao-raw-data-1223-v1-follower'
                            '-worker-1-accef16a-'
                            '317f-440f-8f3f-7dd5b3552d25': {}
                        }
                    }
                }
            }
        }
        return {'flapp': result}

    def delete_custom_object(self,
                             crd_kind,
                             custom_object_name: str,
                             namespace='default'):
        return {
            'kind': crd_kind.value,
            'metadata': {
                'name': custom_object_name,
                'namesapce': namespace
            }
        }

    def list_resource_of_custom_object(self,
                                       crd_kind,
                                       custom_object_name: str,
                                       resource_type: str,
                                       namespace='default'):
        result = {
            'pods': {
                'metadata': {
                    'selfLink': '/api/v1/namespaces/default/pods',
                    'resourceVersion': '780480990'
                }
            },
            'items': [{
                'metadata': {
                    'name': '{}-0'.format(custom_object_name)
                }
            }, {
                'metadata': {
                    'name': '{}-1'.format(custom_object_name)
                }
            }]
        }
        return {'pods': result}

    def create_or_replace_custom_object(self,
                                        crd_kind,
                                        json_object,
                                        namespace='default'):
        return json_object

    def get_webshell_session(self,
                             flapp_name,
                             container_name: str,
                             namespace='default'):
        return {'id': 1}

    def get_sparkapplication(self,
                             name: str,
                             namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        logging.info('======================')
        logging.info(
            f'get spark application, name: {name}, namespace: {namespace}')
        return {
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
                    'state': 'COMPLETED'
                },
            }
        }

    def create_sparkapplication(
            self,
            json_object: dict,
            namespace: str = SPARKOPERATOR_NAMESPACE) -> dict:
        logging.info('======================')
        logging.info(f'create spark application, namespace: {namespace}, '
                     f'json: {json_object}')
        return {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp': '2021-04-15T10:43:15Z',
                'generation': 1,
                'name': 'fl-transformer-yaml',
                'namespace': 'fedlearner',
                'resourceVersion': '348817823',
            },
            'spec': {
                'arguments': [
                    'hdfs://user/feature/data.csv',
                    'hdfs://user/feature/data_tfrecords/'
                ],
            }
        }

    def delete_sparkapplication(self,
                                name: str,
                                namespace: str = SPARKOPERATOR_NAMESPACE
                                ) -> dict:
        logging.info('======================')
        logging.info(
            f'delete spark application, name: {name}, namespace: {namespace}')
        return {
            'kind': 'Status',
            'apiVersion': 'v1',
            'metadata': {},
            'status': 'Success',
            'details': {
                'name': name,
                'group': 'sparkoperator.k8s.io',
                'kind': 'sparkapplications',
                'uid': '790603b6-9dd6-11eb-9282-b8599fb51ea8'
            }
        }
