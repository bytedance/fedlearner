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
import unittest
from datetime import datetime, timezone

from kubernetes.client import V1ObjectMeta, V1OwnerReference

from fedlearner_webconsole.k8s.models import PodState, ContainerState, \
    PodCondition, Pod, FlAppState, FlApp, SparkApp, SparkAppState, FedApp, get_app_name_from_metadata, PodMessage
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.proto.job_pb2 import PodPb


class PodStateTest(unittest.TestCase):

    def test_from_string(self):
        self.assertEqual(PodState.from_value('Running'), PodState.RUNNING)
        self.assertEqual(PodState.from_value('Unknown'), PodState.UNKNOWN)

    def test_from_unknown(self):
        self.assertEqual(PodState.from_value('hhhhhhhh'), PodState.UNKNOWN)


class ContainerStateTest(unittest.TestCase):

    def test_get_message(self):
        state = ContainerState(state='haha', message='test message', reason='test reason')
        self.assertEqual(state.get_message(), 'haha:test reason')
        self.assertEqual(state.get_message(private=True), 'haha:test message')
        state.message = None
        self.assertEqual(state.get_message(), 'haha:test reason')
        self.assertEqual(state.get_message(private=True), 'haha:test reason')


class PodConditionTest(unittest.TestCase):

    def test_get_message(self):
        cond = PodCondition(cond_type='t1', message='test message', reason='test reason')
        self.assertEqual(cond.get_message(), 't1:test reason')
        self.assertEqual(cond.get_message(private=True), 't1:test message')
        cond.message = None
        self.assertEqual(cond.get_message(), 't1:test reason')
        self.assertEqual(cond.get_message(private=True), 't1:test reason')


class PodTest(unittest.TestCase):

    def test_to_proto(self):
        pod = Pod(name='this-is-a-pod',
                  state=PodState.RUNNING,
                  pod_type='WORKER',
                  pod_ip='172.10.0.20',
                  container_states=[ContainerState(state='h1', message='test message')],
                  pod_conditions=[PodCondition(cond_type='h2', reason='test reason')],
                  creation_timestamp=100)
        self.assertEqual(
            pod.to_proto(include_private_info=True),
            PodPb(
                name='this-is-a-pod',
                pod_type='WORKER',
                state='RUNNING',
                pod_ip='172.10.0.20',
                message='h1:test message, h2:test reason',
                creation_timestamp=100,
            ))

    def test_from_json(self):
        creation_timestamp = datetime.utcnow()
        json = {
            'metadata': {
                'name': 'test-pod',
                'labels': {
                    'app-name': 'u244777dac51949c5b2b-data-join-job',
                    'fl-replica-type': 'master'
                },
                'creation_timestamp': creation_timestamp,
            },
            'status': {
                'pod_ip':
                    '172.10.0.20',
                'message':
                    'test',
                'phase':
                    'Running',
                'conditions': [{
                    'type': 'Failed',
                    'reason': 'Test reason'
                }],
                'container_statuses': [{
                    'containerID':
                        'docker://034eaf58d4e24581232832661636da9949b6e2fb05\
                    6398939fc2c0f2809d4c64',
                    'image':
                        'artifact.bytedance.com/fedlearner/fedlearner:438d603',
                    'state': {
                        'running': {
                            'message': 'Test message'
                        }
                    }
                }]
            },
            'spec': {
                'containers': [{
                    'name': 'test-container',
                    'resources': {
                        'limits': {
                            'cpu': '2000m',
                            'memory': '4Gi',
                        },
                        'requests': {
                            'cpu': '2000m',
                            'memory': '4Gi',
                        }
                    }
                }]
            }
        }
        expected_pod = Pod(name='test-pod',
                           state=PodState.RUNNING,
                           pod_type='MASTER',
                           pod_ip='172.10.0.20',
                           container_states=[ContainerState(state='running', message='Test message')],
                           pod_conditions=[PodCondition(cond_type='Failed', reason='Test reason')],
                           creation_timestamp=to_timestamp(creation_timestamp),
                           status_message='test')
        self.assertEqual(Pod.from_json(json), expected_pod)

    def test_get_message(self):
        pod = Pod(name='test',
                  state=PodState.FAILED,
                  container_states=[
                      ContainerState(state='terminated', message='0101010'),
                      ContainerState(state='running', message='11')
                  ])
        self.assertEqual(pod.get_message(True),
                         PodMessage(summary='terminated:0101010', details='terminated:0101010, running:11'))
        self.assertEqual(pod.get_message(False), PodMessage(summary=None, details=''))
        pod.container_states = [ContainerState(state='terminated')]
        self.assertEqual(pod.get_message(True), PodMessage(summary=None, details=''))


class FlAppStateTest(unittest.TestCase):

    def test_from_string(self):
        self.assertEqual(FlAppState.from_value('FLStateComplete'), FlAppState.COMPLETED)
        self.assertEqual(FlAppState.from_value('Unknown'), FlAppState.UNKNOWN)

    def test_from_unknown(self):
        self.assertEqual(FlAppState.from_value('hhh123hhh'), FlAppState.UNKNOWN)


class FlAppTest(unittest.TestCase):

    def test_from_json(self):
        json = {
            'app': {
                'metadata': {
                    'creationTimestamp': '2022-09-27T09:07:01Z',
                },
                'status': {
                    'appState': 'FLStateComplete',
                    'completionTime': '2021-04-26T08:33:45Z',
                    'flReplicaStatus': {
                        'Master': {
                            'active': {
                                'test-pod1': {}
                            },
                            'failed': {
                                'test-pod2': {}
                            },
                        },
                        'Worker': {
                            'succeeded': {
                                'test-pod3': {},
                                'test-pod4': {}
                            }
                        }
                    }
                }
            }
        }
        completed_at = int(datetime(2021, 4, 26, 8, 33, 45, tzinfo=timezone.utc).timestamp())
        expected_flapp = FlApp(state=FlAppState.COMPLETED,
                               completed_at=completed_at,
                               pods=[
                                   Pod(name='test-pod1', state=PodState.RUNNING, pod_type='MASTER'),
                                   Pod(name='test-pod2', state=PodState.FAILED_AND_FREED, pod_type='MASTER'),
                                   Pod(name='test-pod3', state=PodState.SUCCEEDED_AND_FREED, pod_type='WORKER'),
                                   Pod(name='test-pod4', state=PodState.SUCCEEDED_AND_FREED, pod_type='WORKER')
                               ])
        actual_flapp = FlApp.from_json(json)
        self.assertEqual(actual_flapp, expected_flapp)
        self.assertEqual(actual_flapp.is_completed, True)
        self.assertEqual(actual_flapp.completed_at, 1619426025)
        self.assertEqual(actual_flapp.creation_timestamp, 1664269621)


class SparkAppTest(unittest.TestCase):

    def test_from_json(self):
        json = {
            'app': {
                'metadata': {
                    'creationTimestamp': '2022-09-27T09:07:01Z',
                },
                'status': {
                    'applicationState': {
                        'state': 'COMPLETED',
                        'errorMessage': 'OOMKilled'
                    },
                    'driverInfo': {
                        'podName': 'fl-transformer-yaml-driver',
                    },
                    'executionAttempts': 1,
                    'executorState': {
                        'fedlearnertransformer-4a859f78d5210f41-exec-1': 'RUNNING'
                    },
                    'lastSubmissionAttemptTime': '2021-04-15T10:43:28Z',
                    'sparkApplicationId': 'spark-adade63e9071431881d6a16666ec1c87',
                    'submissionAttempts': 1,
                    'submissionID': '37a07c69-516b-48fe-ae70-701eec529eda',
                    'terminationTime': '2021-04-15T10:43:53Z'
                }
            }
        }

        completed_at = int(datetime(2021, 4, 15, 10, 43, 53, tzinfo=timezone.utc).timestamp())
        expected_sparkapp = SparkApp(state=SparkAppState.COMPLETED, completed_at=completed_at, pods=[])
        actual_sparkapp = SparkApp.from_json(json)
        self.assertEqual(actual_sparkapp, expected_sparkapp)
        self.assertEqual(actual_sparkapp.is_completed, True)
        self.assertEqual(actual_sparkapp.is_failed, False)
        self.assertEqual(actual_sparkapp.completed_at, 1618483433)
        self.assertEqual(actual_sparkapp.error_message, 'OOMKilled')
        self.assertEqual(actual_sparkapp.creation_timestamp, 1664269621)


class FedAppTest(unittest.TestCase):

    def test_from_json(self):
        json = {
            'app': {
                'metadata': {
                    'creationTimestamp': '2022-09-27T09:07:01Z',
                },
                'status': {
                    'conditions': [{
                        'type': 'succeeded',
                        'status': 'False',
                        'lastTransitionTime': '2022-01-17T12:06:33Z',
                        'reason': 'OutOfLimitation',
                        'message': 'detail'
                    }]
                }
            }
        }
        fed_app = FedApp.from_json(json)
        self.assertEqual(fed_app.is_failed, True)
        self.assertEqual(fed_app.is_completed, False)
        self.assertEqual(fed_app.completed_at, 1642421193)
        self.assertEqual(fed_app.error_message, 'OutOfLimitation: detail')
        self.assertEqual(fed_app.creation_timestamp, 1664269621)
        json = {'app': {'status': {'conditions': []}}}
        fed_app = FedApp.from_json(json)
        self.assertEqual(fed_app.is_failed, False)
        self.assertEqual(fed_app.is_completed, False)
        self.assertEqual(fed_app.completed_at, 0)
        self.assertEqual(fed_app.creation_timestamp, 0)


class GetAppNameFromMetadataTest(unittest.TestCase):

    def test_pure_pod(self):
        metadata = V1ObjectMeta(
            name='test-pod',
            namespace='fedlearner',
        )
        self.assertIsNone(get_app_name_from_metadata(metadata))

    def test_sparkapp(self):
        metadata = V1ObjectMeta(
            name='test-driver',
            namespace='fedlearner',
            owner_references=[
                V1OwnerReference(
                    api_version='sparkoperator.k8s.io/v1beta2',
                    controller=True,
                    kind='SparkApplication',
                    name='spark-app-name',
                    uid='812c1a48-5585-400f-9174-471d311fbec3',
                )
            ],
            labels={
                'sparkoperator.k8s.io/app-name': 'spark-app-name',
                'sparkoperator.k8s.io/launched-by-spark-operator': 'true',
            },
        )
        self.assertEqual(get_app_name_from_metadata(metadata), 'spark-app-name')
        metadata = V1ObjectMeta(
            name='test-executor',
            namespace='fedlearner',
            owner_references=[
                V1OwnerReference(
                    api_version='v1',
                    controller=True,
                    kind='Pod',
                    name='test-driver',
                    uid='812c1a48-5585-400f-9174-471d311fbec3',
                )
            ],
            labels={
                'sparkoperator.k8s.io/app-name': 'spark-app-name',
            },
        )
        self.assertEqual(get_app_name_from_metadata(metadata), 'spark-app-name')

    def test_fedapp(self):
        metadata = V1ObjectMeta(name='test-pod',
                                namespace='default',
                                owner_references=[
                                    V1OwnerReference(
                                        api_version='fedlearner.k8s.io/v1alpha1',
                                        controller=True,
                                        kind='FedApp',
                                        name='test-fedapp-job',
                                        uid='bcf5324c-aa2b-4918-bdee-42ac464e18d5',
                                    )
                                ])
        self.assertEqual(get_app_name_from_metadata(metadata), 'test-fedapp-job')

    def test_flapp(self):
        metadata = V1ObjectMeta(name='test-pod',
                                namespace='fedlearner',
                                owner_references=[
                                    V1OwnerReference(
                                        api_version='fedlearner.k8s.io/v1alpha1',
                                        controller=True,
                                        kind='FLApp',
                                        name='u130eaab6eec64552945-nn-model',
                                        uid='bcf5324c-aa2b-4918-bdee-42ac464e18d5',
                                    )
                                ])
        self.assertEqual(get_app_name_from_metadata(metadata), 'u130eaab6eec64552945-nn-model')

    def test_unknown_metadata(self):
        metadata = V1ObjectMeta(name='test-pod',
                                namespace='fedlearner',
                                owner_references=[
                                    V1OwnerReference(
                                        api_version='fedlearner.k8s.io/v1alpha1',
                                        controller=True,
                                        kind='NewApp',
                                        name='u130eaab6eec64552945-nn-model',
                                        uid='bcf5324c-aa2b-4918-bdee-42ac464e18d5',
                                    )
                                ])
        self.assertIsNone(get_app_name_from_metadata(metadata))


if __name__ == '__main__':
    unittest.main()
