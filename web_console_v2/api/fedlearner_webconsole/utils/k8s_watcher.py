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
import enum
import logging
import threading
import queue
import traceback
from http import HTTPStatus
from kubernetes import client, watch
from envs import Envs
from fedlearner_webconsole.utils.k8s_cache import k8s_cache, \
    Event, ObjectType

class CrdKind(enum.Enum):
    FLAPP = 'flapps'
    SPARK_APPLICATION = 'sparkapplications'


FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'




class K8sWatcher(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._api = None
        self._crds = None
        self._flapp_watch = None
        self._pods_watch = None
        self._flapp_watch_thread = None
        self._pods_watch_thread = None
        self._event_consumer_thread = None

        # https://stackoverflow.com/questions/62223424/
        # simplequeue-vs-queue-in-python-what-is-the-
        # advantage-of-using-simplequeue
        # if use simplequeue, put opt never block.
        # TODO(xiangyuxuan): change to simplequeue
        self._queue = queue.Queue()
        self._cache = {}
        self._cache_lock = threading.Lock()

    def initial(self):
        self._api = client.CoreV1Api()
        self._crds = client.CustomObjectsApi()
        self._flapp_watch = watch.Watch()
        self._pods_watch = watch.Watch()

    def start(self):
        with self._lock:
            if self._running:
                logging.warning('K8s watcher has already started')
                return
            self._running = True
            self._flapp_watch_thread = threading.Thread(
                target=self._k8s_flapp_watcher,
                name='flapp_watcher',
                daemon=True)
            self._pods_watch_thread = threading.Thread(
                target=self._k8s_pods_watch,
                name='pods_watcher',
                daemon=True)
            self._event_consumer_thread = threading.Thread(
                target=self._event_consumer,
                name='cache_consumer',
                daemon=True)
            self._pods_watch_thread.start()
            self._flapp_watch_thread.start()
            self._event_consumer_thread.start()
            logging.info('K8s watcher started')

    def _event_consumer(self):
        # TODO(xiangyuxuan): do more business level operations
        while True:
            try:
                event = self._queue.get()
                k8s_cache.update_cache(event)
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s event_consumer : {str(e)}. '
                              f'traceback:{traceback.format_exc()}')

    def _k8s_flapp_watcher(self):
        # init cache for flapp
        resource_version = '0'
        while True:
            if not self._running:
                break
            stream = self._flapp_watch.stream(
                self._crds.list_namespaced_custom_object,
                group=FEDLEARNER_CUSTOM_GROUP,
                version=FEDLEARNER_CUSTOM_VERSION,
                namespace=Envs.K8S_NAMESPACE,
                plural='flapps',
                resource_version=resource_version
            )
            try:
                for event in stream:

                    self._produce_event(event, ObjectType.FLAPP)

                    metadata = event['object'].get('metadata')
                    if metadata['resourceVersion'] is not None:
                        resource_version = metadata['resourceVersion']
                        logging.debug(
                            'resource_version now: {0}'.format(
                                resource_version))
            except client.exceptions.ApiException as e:
                logging.error(f'watcher:{str(e)}')
                if e.status == HTTPStatus.GONE:
                    # resource_version has been too old, cache should be relist
                    resource_version = '0'
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s watcher gets event error: {str(e)}',
                              exc_info=True)

    def _produce_event(self, event, obj_type):
        self._queue.put(Event.from_json(event, obj_type))

    def _k8s_pods_watch(self):
        # init cache for flapp
        resource_version = '0'
        while True:
            if not self._running:
                break
            stream = self._pods_watch.stream(
                self._api.list_namespaced_pod,
                namespace=Envs.K8S_NAMESPACE,
                label_selector='app-name',
                resource_version=resource_version
            )

            try:
                for event in stream:
                    self._produce_event(event, ObjectType.POD)
                    metadata = event['object'].metadata
                    if metadata.resource_version is not None:
                        resource_version = metadata.resource_version
                        logging.debug(
                            'resource_version now: {0}'.format(
                                resource_version))
            except client.exceptions.ApiException as e:
                logging.error(f'watcher:{str(e)}')
                if e.status == HTTPStatus.GONE:
                    resource_version = '0'
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s watcher gets event error: {str(e)}',
                              exc_info=True)


k8s_watcher = K8sWatcher()
