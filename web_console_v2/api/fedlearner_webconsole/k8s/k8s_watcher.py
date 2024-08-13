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
from abc import ABC, abstractmethod
import logging
import multiprocessing
import threading
import queue
import traceback
from http import HTTPStatus
from typing import Generator, NamedTuple, Optional, Tuple
from kubernetes import client, watch
from kubernetes.client import V1ObjectMeta
from envs import Envs
from fedlearner_webconsole.job.event_listener import JobEventListener
from fedlearner_webconsole.k8s.k8s_cache import k8s_cache, Event, ObjectType
from fedlearner_webconsole.utils.metrics import emit_store, emit_counter
from fedlearner_webconsole.k8s.k8s_client import k8s_client
from fedlearner_webconsole.k8s.models import CrdKind, get_app_name_from_metadata
from fedlearner_webconsole.mmgr.event_listener import ModelEventListener


class CrdWatcherConfig(NamedTuple):
    version: str
    group: str
    plural: str
    object_type: ObjectType


WATCHER_CONFIG = {
    CrdKind.FLAPP:
        CrdWatcherConfig(
            version='v1alpha1',
            group='fedlearner.k8s.io',
            plural='flapps',
            object_type=ObjectType.FLAPP,
        ),
    CrdKind.SPARKAPPLICATION:
        CrdWatcherConfig(
            version='v1beta2',
            group='sparkoperator.k8s.io',
            plural='sparkapplications',
            object_type=ObjectType.SPARKAPP,
        ),
    CrdKind.FEDAPP:
        CrdWatcherConfig(
            version='v1alpha1',
            group='fedlearner.k8s.io',
            plural='fedapps',
            object_type=ObjectType.FEDAPP,
        ),
}

_REQUEST_TIMEOUT_IN_SECOND = 900


class AbstractWatcher(ABC):

    @property
    @abstractmethod
    def kind(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def _watch(self, watcher: watch.Watch, resource_version: str) -> Generator[Tuple[Event, Optional[str]], None, None]:
        """An abstract method which subclasses should implement it to watch and procedue events."""
        raise NotImplementedError()

    def _watch_forever(self, event_queue: 'queue.Queue[Event]'):
        """Watches forever, which handles a lot of exceptions and make the watcher always work (hopefully)."""
        # resource_version '0' means getting a recent resource without
        # consistency guarantee, this is to reduce the load of etcd.
        # Ref: https://kubernetes.io/docs/reference/using-api/api-concepts/ #the-resourceversion-parameter
        resource_version = '0'
        watcher = watch.Watch()
        while True:
            try:
                logging.info(f'[K8s watcher] [{self.kind}] start watching, resource version: {resource_version}')
                # Each round we re-watch to k8s
                watch_stream = self._watch(watcher, resource_version)
                emit_counter('k8s.watcher.watch', 1, tags={'kind': self.kind})
                for (event, new_version) in watch_stream:
                    if new_version:
                        # Updates newest resource version, note that resource version is string,
                        # using max is a little hacky.
                        resource_version = max(resource_version, new_version)
                    logging.debug(f'[K8s watcher] [{self.kind}] new resource version: {new_version}')
                    event_queue.put(event)
            except client.exceptions.ApiException as e:
                logging.exception(f'[K8s watcher] [{self.kind}] API error')
                if e.status == HTTPStatus.GONE:
                    # It has been too old, resources should be relisted
                    resource_version = '0'
                # TODO(xiangyuxuan.prs): remove in the future.
                elif e.status == HTTPStatus.NOT_FOUND:
                    logging.exception(f'[K8s watcher] [{self.kind}] unsupported')
                    break
            except Exception as e:  # pylint: disable=broad-except
                logging.exception(f'[K8s watcher] [{self.kind}] unexpected error')
        watcher.stop()

    def run(self, event_queue: queue.Queue, retry_timeout_in_second: int):
        """Starts the watcher.

        Historically the watcher (process) may hang and never send the requests to k8s API server,
        so this is a workaround to retry after timeout.

        Args:
            event_queue: A queue to passthrough the events from watcher.
            retry_timeout_in_second: If no event received within this threshold, the watcher gets restarted.
        """
        mp_context = multiprocessing.get_context('spawn')
        internal_queue = mp_context.Queue()
        process_name = f'k8s-watcher-{self.kind}'
        process = mp_context.Process(name=process_name, daemon=True, target=self._watch_forever, args=(internal_queue,))
        process.start()
        logging.info(f'[K8s watcher] [{self.kind}] process started')
        while True:
            try:
                # Waits for a new event with timeout, if it gets stuck, then we restart the watcher.
                event = internal_queue.get(timeout=retry_timeout_in_second)
                # Puts to outside
                event_queue.put(event)
            except queue.Empty:
                logging.info(f'[K8s watcher] [{self.kind}] no event in queue, restarting...')
                process.terminate()
                process.join()
                # TODO(wangsen.0914): add process.close() here after upgrade to python 3.8
                internal_queue.close()
                internal_queue = mp_context.Queue()
                process = mp_context.Process(name=process_name,
                                             daemon=True,
                                             target=self._watch_forever,
                                             args=(internal_queue,))
                process.start()
                logging.info(f'[K8s watcher] [{self.kind}] process restarted')


class PodWatcher(AbstractWatcher):

    @property
    def kind(self) -> str:
        return ObjectType.POD.name

    def _watch(self, watcher: watch.Watch, resource_version: str) -> Generator[Tuple[Event, Optional[str]], None, None]:
        stream = watcher.stream(
            k8s_client.core.list_namespaced_pod,
            namespace=Envs.K8S_NAMESPACE,
            resource_version=resource_version,
            # Sometimes watch gets stuck
            _request_timeout=_REQUEST_TIMEOUT_IN_SECOND,
        )
        for event in stream:
            metadata: V1ObjectMeta = event['object'].metadata
            if get_app_name_from_metadata(metadata):
                yield Event.from_json(event, ObjectType.POD), metadata.resource_version


class CrdWatcher(AbstractWatcher):

    def __init__(self, config: CrdWatcherConfig):
        super().__init__()
        self.config = config

    @property
    def kind(self) -> str:
        return self.config.object_type.name

    def _watch(self, watcher: watch.Watch, resource_version: str) -> Generator[Tuple[Event, Optional[str]], None, None]:
        stream = watcher.stream(
            k8s_client.crds.list_namespaced_custom_object,
            group=self.config.group,
            version=self.config.version,
            namespace=Envs.K8S_NAMESPACE,
            plural=self.config.plural,
            resource_version=resource_version,
            # Sometimes watch gets stuck
            _request_timeout=_REQUEST_TIMEOUT_IN_SECOND,
        )
        for event in stream:
            new_resource_version = event['object'].get('metadata', {}).get('resourceVersion', None)
            yield Event.from_json(event, self.config.object_type), new_resource_version


class K8sWatcher(object):

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._event_consumer_thread = None
        self._event_listeners = [JobEventListener(), ModelEventListener()]

        # https://stackoverflow.com/questions/62223424/simplequeue-vs-queue-in-python-what-is-the-advantage-of-using-simplequeue
        # if use simplequeue, put opt never block.
        # TODO(xiangyuxuan): change to simplequeue
        self._queue = queue.Queue()
        self._cache = {}
        self._cache_lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._running:
                logging.warning('K8s watcher has already started')
                return
            self._running = True

            watchers = [PodWatcher()]
            for _, crd_config in WATCHER_CONFIG.items():
                watchers.append(CrdWatcher(config=crd_config))
            watcher_threads = [
                threading.Thread(
                    name=f'k8s-watcher-{watcher.kind}',
                    target=watcher.run,
                    args=(
                        self._queue,
                        # Keep consistent with k8s watcher event timeout
                        _REQUEST_TIMEOUT_IN_SECOND,
                    ),
                    daemon=True,
                ) for watcher in watchers
            ]

            self._event_consumer_thread = threading.Thread(target=self._event_consumer,
                                                           name='cache_consumer',
                                                           daemon=True)
            for wthread in watcher_threads:
                wthread.start()
            self._event_consumer_thread.start()
            logging.info('K8s watcher started')

    def _event_consumer(self):
        # TODO(xiangyuxuan): do more business level operations
        while True:
            try:
                event = self._queue.get()
                k8s_cache.update_cache(event)
                self._listen_crd_event(event)
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s event_consumer : {str(e)}. ' f'traceback:{traceback.format_exc()}')

    def _listen_crd_event(self, event: Event):
        if event.obj_type == ObjectType.POD:
            return
        for listener in self._event_listeners:
            try:
                listener.update(event)
            # pylint: disable=broad-except
            except Exception as e:
                emit_store('event_listener_update_error', 1)
                logging.warning(f'[K8sWatcher] listener update with error {str(e)}')


k8s_watcher = K8sWatcher()
