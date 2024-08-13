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
# pylint: disable=logging-format-interpolation
import logging
import datetime
import time

from kubernetes import client

from testing.helpers import to_simple_namespace

_RAISE_EXCEPTION_KEY = 'raise_exception'


class FakeResponse(object):

    def read_chunked(self, *args, **kwargs):
        return []

    def close(self):
        pass

    def release_conn(self):
        pass


class FakeCoreApi(object):

    def __init__(self, timeouts=10):
        # timeout in second
        self.timeouts = timeouts

    def list_namespaced_pod(self, namespace, **kwargs):
        time.sleep(self.timeouts)
        return FakeResponse()


class FakeCrdsApi(object):

    def __init__(self, timeouts=10):
        # timeout in second
        self.timeouts = timeouts

    def list_namespaced_custom_object(self, namespace, **kwargs):
        time.sleep(self.timeouts)
        return FakeResponse()

    def get_namespaced_custom_object(self, *args, **kwargs):
        return FakeResponse()


class FakeK8sClient(object):
    """A fake k8s client for development.

    With this client we can decouple the dependency of k8s cluster.
    """

    def __init__(self):
        self.core = FakeCoreApi(60)
        self.crds = FakeCrdsApi(60)

    def close(self):
        pass

    def create_or_update_secret(self, data, metadata, secret_type, name, namespace='default'):
        # User may pass two type of data:
        # 1. dictionary
        # 2. K8s Object
        # They are both accepted by real K8s client,
        # but K8s Object is not iterable.
        if isinstance(data, dict) and _RAISE_EXCEPTION_KEY in data:
            raise RuntimeError('[500] Fake exception for save_secret')
        # Otherwise succeeds
        logging.info('======================')
        logging.info(f'Saved a secret with: data: {data}, ' 'metadata: {metadata}, type: {secret_type}')

    def delete_secret(self, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Deleted a secret with: name: {name}')

    def get_secret(self, name, namespace='default'):
        return client.V1Secret(api_version='v1',
                               data={'test': 'test'},
                               kind='Secret',
                               metadata={
                                   'name': name,
                                   'namespace': namespace
                               },
                               type='Opaque')

    def create_or_update_service(self, metadata, spec, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Saved a service with: spec: {spec}, metadata: {metadata}')

    def delete_service(self, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Deleted a service with: name: {name}')

    def get_service(self, name, namespace='default'):
        return client.V1Service(api_version='v1',
                                kind='Service',
                                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                                spec=client.V1ServiceSpec(selector={'app': 'nginx'}))

    def list_service(self, namespace='default'):
        service_dict = {'items': [{'metadata': {'name': f'fl-{i * 3}'}} for i in 'ac']}
        return to_simple_namespace(service_dict)

    def create_or_update_ingress(self, metadata, spec, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Saved a ingress with: spec: {spec}, metadata: {metadata}')

    def delete_ingress(self, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Deleted a ingress with: name: {name}')

    def get_ingress(self, name, namespace='default'):
        return client.NetworkingV1beta1Ingress(api_version='networking.k8s.io/v1beta1',
                                               kind='Ingress',
                                               metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                                               spec=client.NetworkingV1beta1IngressSpec())

    def list_ingress(self, namespace='default'):
        ingress_dict = {'items': [{'metadata': {'name': f'fl-{i * 3}-client-auth'}} for i in 'abc']}
        return to_simple_namespace(ingress_dict)

    def create_or_update_deployment(self, metadata, spec, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Saved a deployment with: spec: {spec}, metadata: {metadata}')

    def delete_deployment(self, name, namespace='default'):
        logging.info('======================')
        logging.info(f'Deleted a deployment with: name: {name}')

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
                    containers=[client.V1Container(name='fedlearner-operator', args=['test'])]))))

    def delete_app(self, app_name, group, version: str, plural: str, namespace: str = 'default'):
        pass

    def create_app(self, app_name, group, version: str, plural: str, namespace: str = 'default') -> dict:
        return {}

    def get_app_cache(self, app_name):
        pods = {
            'pods': {
                'metadata': {
                    'selfLink': '/api/v1/namespaces/default/pods',
                    'resourceVersion': '780480990'
                }
            },
            'items': [{
                'metadata': {
                    'name': f'{app_name}-0'
                }
            }, {
                'metadata': {
                    'name': f'{app_name}-1'
                }
            }]
        }
        flapp = {
            'kind': 'FLAPP',
            'metadata': {
                'name': app_name,
                'namesapce': 'default'
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
        return {'flapp': flapp, 'pods': pods}

    def get_sparkapplication(self, name: str, namespace: str = 'default') -> dict:
        logging.info('======================')
        logging.info(f'get spark application, name: {name}, namespace: {namespace}')
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

    def create_sparkapplication(self, json_object: dict, namespace: str = 'default') -> dict:
        logging.info('======================')
        logging.info(f'create spark application, namespace: {namespace}, ' f'json: {json_object}')
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
                'arguments': ['hdfs://user/feature/data.csv', 'hdfs://user/feature/data_tfrecords/'],
            }
        }

    def delete_sparkapplication(self, name: str, namespace: str = 'default') -> dict:
        logging.info('======================')
        logging.info(f'delete spark application, name: {name}, namespace: {namespace}')
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

    def get_pod_log(self, name: str, namespace: str, tail_lines: int):
        return str(datetime.datetime.now())

    def get_pods(self, namespace, label_selector):
        fake_pod = client.V1Pod(metadata=client.V1ObjectMeta(name='fake_pod',
                                                             labels={},
                                                             creation_timestamp=datetime.datetime.utcnow()),
                                status=client.V1PodStatus(phase='Running'),
                                spec=client.V1PodSpec(containers=[
                                    client.V1Container(name='fake_container',
                                                       resources=client.V1ResourceRequirements(limits={
                                                           'cpu': '2000m',
                                                           'memory': '4Gi'
                                                       },
                                                                                               requests={
                                                                                                   'cpu': '2000m',
                                                                                                   'memory': '4Gi'
                                                                                               }))
                                ]))
        return client.V1PodList(items=[fake_pod])
