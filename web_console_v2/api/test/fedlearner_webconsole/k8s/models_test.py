# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

from fedlearner_webconsole.k8s.models import PodType, PodState, ContainerState, PodCondition, Pod, FlAppState, FlApp


class PodTypeTest(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(PodType.from_value('master'), PodType.MASTER)
        self.assertEqual(PodType.from_value('Ps'), PodType.PS)
        self.assertEqual(PodType.from_value('WORKER'),
                         PodType.WORKER)

    def test_from_unknown(self):
        self.assertEqual(PodType.from_value('hhhhhhhh'),
                         PodType.UNKNOWN)
        self.assertEqual(PodType.from_value(1),
                         PodType.UNKNOWN)


class PodStateTest(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(PodState.from_value('Running'), PodState.RUNNING)
        self.assertEqual(PodState.from_value('Unknown'), PodState.UNKNOWN)

    def test_from_unknown(self):
        self.assertEqual(PodState.from_value('hhhhhhhh'),
                         PodState.UNKNOWN)


class ContainerStateTest(unittest.TestCase):
    def test_get_message(self):
        state = ContainerState(state='haha',
                               message='test message',
                               reason='test reason')
        self.assertEqual(state.get_message(), 'haha:test reason')
        self.assertEqual(state.get_message(private=True), 'haha:test message')
        state.message = None
        self.assertEqual(state.get_message(), 'haha:test reason')
        self.assertEqual(state.get_message(private=True), 'haha:test reason')


class PodConditionTest(unittest.TestCase):
    def test_get_message(self):
        cond = PodCondition(cond_type='t1',
                            message='test message',
                            reason='test reason')
        self.assertEqual(cond.get_message(), 't1:test reason')
        self.assertEqual(cond.get_message(private=True), 't1:test message')
        cond.message = None
        self.assertEqual(cond.get_message(), 't1:test reason')
        self.assertEqual(cond.get_message(private=True), 't1:test reason')


class PodTest(unittest.TestCase):
    def test_to_dict(self):
        pod = Pod(name='this-is-a-pod',
                  state=PodState.RUNNING,
                  pod_type=PodType.WORKER,
                  pod_ip='172.10.0.20',
                  container_states=[ContainerState(
                      state='h1',
                      message='test message'
                  )],
                  pod_conditions=[PodCondition(
                      cond_type='h2',
                      reason='test reason'
                  )])
        self.assertEqual(pod.to_dict(include_private_info=True),
                         {
                             'name': 'this-is-a-pod',
                             'pod_type': 'WORKER',
                             'state': 'RUNNING',
                             'pod_ip': '172.10.0.20',
                             'message': 'h1:test message, h2:test reason'
                         })

    def test_from_json(self):
        json = {
            'metadata': {
                'name': 'test-pod',
                'labels': {
                    'app-name': 'u244777dac51949c5b2b-data-join-job',
                    'fl-replica-type': 'master'
                },
            },
            'status': {
                'pod_ip': '172.10.0.20',
                'phase': 'Running',
                'conditions': [
                    {
                        'type': 'Failed',
                        'reason': 'Test reason'
                    }
                ],
                'containerStatuses': [
                    {
                        'containerID': 'docker://034eaf58d4e24581232832661636da9949b6e2fb056398939fc2c0f2809d4c64',
                        'image': 'artifact.bytedance.com/fedlearner/fedlearner:438d603',
                        'state': {
                            'running': {
                                'message': 'Test message'
                            }
                        }
                    }
                ]
            }
        }
        expected_pod = Pod(
            name='test-pod',
            state=PodState.RUNNING,
            pod_type=PodType.MASTER,
            pod_ip='172.10.0.20',
            container_states=[
                ContainerState(
                    state='running',
                    message='Test message'
                )
            ],
            pod_conditions=[
                PodCondition(
                    cond_type='Failed',
                    reason='Test reason'
                )
            ]
        )
        self.assertEqual(Pod.from_json(json), expected_pod)


class FlAppStateTest(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(FlAppState.from_value('FLStateComplete'),
                         FlAppState.COMPLETED)
        self.assertEqual(FlAppState.from_value('Unknown'), FlAppState.UNKNOWN)

    def test_from_unknown(self):
        self.assertEqual(FlAppState.from_value('hhh123hhh'),
                         FlAppState.UNKNOWN)


class FlAppTest(unittest.TestCase):
    def test_from_json(self):
        json = {
            'status': {
                'appState': 'FLStateComplete',
                'completionTime': '2021-04-26T08:33:45Z',
                'flReplicaStatus': {
                    'Master': {
                        'failed': {
                            'test-pod1': {}
                        }
                    },
                    'Worker': {
                        'succeeded': {
                            'test-pod2': {},
                            'test-pod3': {}
                        }
                    }
                }
            }
        }
        completed_at = int(datetime(2021, 4, 26, 8, 33, 45, tzinfo=timezone.utc).timestamp())
        expected_flapp = FlApp(
            state=FlAppState.COMPLETED,
            completed_at=completed_at,
            pods=[
                Pod(
                    name='test-pod1',
                    state=PodState.FAILED_AND_FREED,
                    pod_type=PodType.MASTER
                ),
                Pod(
                    name='test-pod2',
                    state=PodState.SUCCEEDED_AND_FREED,
                    pod_type=PodType.WORKER
                ),
                Pod(
                    name='test-pod3',
                    state=PodState.SUCCEEDED_AND_FREED,
                    pod_type=PodType.WORKER
                )
            ]
        )
        self.assertEqual(FlApp.from_json(json), expected_flapp)


if __name__ == '__main__':
    unittest.main()
