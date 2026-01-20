# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from http import HTTPStatus
import multiprocessing
import threading
from typing import Callable, Generator, List, NamedTuple, Optional, Tuple
import unittest
from unittest.mock import MagicMock, Mock, patch
from kubernetes import client, watch
from kubernetes.client import V1Pod, V1ObjectMeta, V1OwnerReference

from fedlearner_webconsole.k8s.k8s_watcher import AbstractWatcher, CrdWatcher, CrdWatcherConfig, PodWatcher
from fedlearner_webconsole.k8s.k8s_cache import Event, EventType, ObjectType


class Response(NamedTuple):
    # gone/unknown/not_found/normal
    type: str
    events: Optional[List[Event]]


# Why using fake implementation instead of mock?
# because mock does not work in multiprocessing
class FakeWatcher(AbstractWatcher):

    def __init__(self, resp_sequence: Optional[List[Response]]):
        super().__init__()
        self.calls = []
        self._resp_sequence = resp_sequence or []
        self._round = 0

    @property
    def kind(self) -> str:
        return 'fake'

    def _watch(self, watcher: watch.Watch, resource_version: str) -> Generator[Tuple[Event, Optional[str]], None, None]:
        assert isinstance(watcher, watch.Watch)
        self.calls.append(resource_version)
        if self._round < len(self._resp_sequence):
            resp = self._resp_sequence[self._round]
            self._round += 1
            if resp.type == 'gone':
                raise client.exceptions.ApiException(status=HTTPStatus.GONE)
            if resp.type == 'not_found':
                raise client.exceptions.ApiException(status=HTTPStatus.NOT_FOUND)
            if resp.type == 'unknown':
                raise RuntimeError('fake unknown')
            for i, event in enumerate(resp.events or []):
                yield event, str(i)
            return
        # Dead loop
        while True:
            pass


def _fake_event_from_json(event, object_type):
    return event, object_type


class AbstractWatcherTest(unittest.TestCase):

    def _start_thread(self, func: Callable, args) -> threading.Thread:
        t = threading.Thread(daemon=True, target=func, args=args)
        t.start()
        return t

    def test_watch_normally(self):
        events = [
            Event(app_name='t1', event_type=EventType.ADDED, obj_type=ObjectType.POD, obj_dict={}),
            Event(app_name='t2', event_type=EventType.MODIFIED, obj_type=ObjectType.POD, obj_dict={}),
            Event(app_name='t3', event_type=EventType.MODIFIED, obj_type=ObjectType.POD, obj_dict={}),
        ]

        watcher = FakeWatcher(resp_sequence=[
            Response(type='normal', events=events),
        ])
        q = multiprocessing.Queue()
        self._start_thread(watcher.run, args=(
            q,
            1000,
        ))
        actual_events = [q.get(), q.get(), q.get()]
        q.close()

        app_names = [e.app_name for e in actual_events]
        self.assertEqual(app_names, ['t1', 't2', 't3'])

    def test_watch_k8s_api_gone(self):
        events = [
            Event(app_name='t1', event_type=EventType.ADDED, obj_type=ObjectType.POD, obj_dict={}),
            Event(app_name='t2', event_type=EventType.MODIFIED, obj_type=ObjectType.POD, obj_dict={}),
        ]

        watcher = FakeWatcher(resp_sequence=[
            Response(type='gone', events=None),
            Response(type='normal', events=events),
        ])
        q = multiprocessing.Queue()
        self._start_thread(watcher.run, args=(
            q,
            1000,
        ))
        actual_events = [q.get(), q.get()]
        q.close()

        app_names = [e.app_name for e in actual_events]
        self.assertEqual(app_names, ['t1', 't2'])

    def test_watch_unknown_k8s_error(self):
        events1 = [
            Event(app_name='t1', event_type=EventType.ADDED, obj_type=ObjectType.POD, obj_dict={}),
            Event(app_name='t2', event_type=EventType.MODIFIED, obj_type=ObjectType.POD, obj_dict={}),
        ]
        events2 = [
            Event(app_name='t3', event_type=EventType.ADDED, obj_type=ObjectType.POD, obj_dict={}),
        ]

        watcher = FakeWatcher(resp_sequence=[
            Response(type='normal', events=events1),
            Response(type='unknown', events=None),
            Response(type='normal', events=events2),
        ])
        q = multiprocessing.Queue()
        self._start_thread(watcher.run, args=(
            q,
            1000,
        ))
        actual_events = [q.get(), q.get(), q.get()]
        q.close()

        app_names = [e.app_name for e in actual_events]
        self.assertEqual(app_names, ['t1', 't2', 't3'])

    def test_watch_client_hangs(self):
        events = [
            Event(app_name='t1', event_type=EventType.ADDED, obj_type=ObjectType.POD, obj_dict={}),
            Event(app_name='t2', event_type=EventType.MODIFIED, obj_type=ObjectType.POD, obj_dict={}),
        ]

        watcher = FakeWatcher(resp_sequence=[
            Response(type='normal', events=events),
        ])
        q = multiprocessing.Queue()
        self._start_thread(watcher.run, args=(
            q,
            15,
        ))
        # If no event in 10s the client will re-watch, so there should be at least 4 threads
        actual_events = [q.get(), q.get(), q.get(), q.get()]
        q.close()

        app_names = [e.app_name for e in actual_events]
        self.assertEqual(app_names, ['t1', 't2', 't1', 't2'])


class PodWatcherTest(unittest.TestCase):

    def test_kind(self):
        watcher = PodWatcher()
        self.assertEqual(watcher.kind, 'POD')

    @patch('fedlearner_webconsole.k8s.k8s_watcher.Envs.K8S_NAMESPACE', 'fedlearner')
    @patch('fedlearner_webconsole.k8s.k8s_watcher.Event.from_json', _fake_event_from_json)
    @patch('fedlearner_webconsole.k8s.k8s_watcher.k8s_client')
    def test_watch(self, mock_k8s_client: Mock):
        mock_k8s_client.return_value = MagicMock(core=MagicMock(list_namespaced_pod=MagicMock()))
        events = [
            {
                'object':
                    V1Pod(metadata=V1ObjectMeta(
                        resource_version='123',
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
                    )),
            },
            {
                'object':
                    V1Pod(metadata=V1ObjectMeta(
                        resource_version='234',
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
                    )),
            },
        ]
        mock_stream = MagicMock(return_value=events)
        mock_watcher_client = MagicMock(stream=mock_stream)

        watcher = PodWatcher()
        self.assertEqual(
            list(watcher._watch(mock_watcher_client, '0')),  # pylint: disable=protected-access
            [
                ((events[0], ObjectType.POD), '123'),
                ((events[1], ObjectType.POD), '234'),
            ])
        mock_stream.assert_called_once_with(
            mock_k8s_client.core.list_namespaced_pod,
            namespace='fedlearner',
            resource_version='0',
            _request_timeout=900,
        )


class CrdWatcherTest(unittest.TestCase):
    WATCHER_CONFIG = CrdWatcherConfig(
        version='v1alpha1',
        group='fedlearner.k8s.io',
        plural='fedapps',
        object_type=ObjectType.FEDAPP,
    )

    def test_kind(self):
        watcher = CrdWatcher(self.WATCHER_CONFIG)
        self.assertEqual(watcher.kind, 'FEDAPP')

    @patch('fedlearner_webconsole.k8s.k8s_watcher.Envs.K8S_NAMESPACE', 'fedlearner')
    @patch('fedlearner_webconsole.k8s.k8s_watcher.Event.from_json', _fake_event_from_json)
    @patch('fedlearner_webconsole.k8s.k8s_watcher.k8s_client')
    def test_watch(self, mock_k8s_client: Mock):
        mock_k8s_client.return_value = MagicMock(crds=MagicMock(list_namespaced_custom_object=MagicMock()))
        events = [
            {
                'object': {
                    'metadata': {
                        'resourceVersion': '1111',
                    },
                },
            },
            {
                'object': {
                    'metadata': {
                        'resourceVersion': '2222',
                    },
                },
            },
        ]
        mock_stream = MagicMock(return_value=events)
        mock_watcher_client = MagicMock(stream=mock_stream)

        watcher = CrdWatcher(self.WATCHER_CONFIG)
        self.assertEqual(
            list(watcher._watch(mock_watcher_client, '1000')),  # pylint: disable=protected-access
            [
                ((events[0], ObjectType.FEDAPP), '1111'),
                ((events[1], ObjectType.FEDAPP), '2222'),
            ])
        mock_stream.assert_called_once_with(
            mock_k8s_client.crds.list_namespaced_custom_object,
            group=self.WATCHER_CONFIG.group,
            version=self.WATCHER_CONFIG.version,
            namespace='fedlearner',
            plural=self.WATCHER_CONFIG.plural,
            resource_version='1000',
            _request_timeout=900,
        )


if __name__ == '__main__':
    unittest.main()
