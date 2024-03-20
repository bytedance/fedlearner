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
import logging
import threading
import queue
import traceback
from http import HTTPStatus
from kubernetes import client, watch
from envs import Envs, Features
from fedlearner_webconsole.utils.k8s_cache import k8s_cache, \
    Event, ObjectType
from fedlearner_webconsole.utils.k8s_client import (
    k8s_client, FEDLEARNER_CUSTOM_GROUP,
    FEDLEARNER_CUSTOM_VERSION)
from fedlearner_webconsole.mmgr.service import ModelService
from fedlearner_webconsole.db import make_session_context
from fedlearner_webconsole.job.service import JobService


session_context = make_session_context()

class K8sWatcher(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
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
                # job state must be updated before model service
                self._update_hook(event)
                if Features.FEATURE_MODEL_K8S_HOOK:
                    with session_context() as session:
                        ModelService(session).k8s_watcher_hook(event)
                        session.commit()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s event_consumer : {str(e)}. '
                              f'traceback:{traceback.format_exc()}')

    def _update_hook(self, event: Event):
        if event.obj_type == ObjectType.FLAPP:
            logging.debug('[k8s_watcher][_update_hook]receive event %s',
                          event.flapp_name)
            with session_context() as session:
                JobService(session).update_running_state(event.flapp_name)
                session.commit()

    def _k8s_flapp_watcher(self):
        resource_version = '0'
        watcher = watch.Watch()
        while True:
            logging.info(f'new stream of flapps watch rv:{resource_version}')
            if not self._running:
                watcher.stop()
                break
            # resource_version '0' means getting a recent resource without
            # consistency guarantee, this is to reduce the load of etcd.
            # Ref: https://kubernetes.io/docs/reference/using-api
            # /api-concepts/ #the-resourceversion-parameter
            stream = watcher.stream(
                k8s_client.crds.list_namespaced_custom_object,
                group=FEDLEARNER_CUSTOM_GROUP,
                version=FEDLEARNER_CUSTOM_VERSION,
                namespace=Envs.K8S_NAMESPACE,
                plural='flapps',
                resource_version=resource_version,
                _request_timeout=900,  # Sometimes watch gets stuck
            )
            try:
                for event in stream:

                    self._produce_event(event, ObjectType.FLAPP)

                    metadata = event['object'].get('metadata')
                    if metadata['resourceVersion'] is not None:
                        resource_version = max(metadata['resourceVersion'],
                                               resource_version)
                        logging.debug(
                            f'resource_version now: {resource_version}')
            except client.exceptions.ApiException as e:
                logging.error(f'watcher:{str(e)}')
                if e.status == HTTPStatus.GONE:
                    # It has been too old, resources should be relisted
                    resource_version = '0'
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s watcher gets event error: {str(e)}',
                              exc_info=True)

    def _produce_event(self, event, obj_type):
        self._queue.put(Event.from_json(event, obj_type))

    def _k8s_pods_watch(self):
        resource_version = '0'
        watcher = watch.Watch()
        while True:
            logging.info(f'new stream of pods watch rv: {resource_version}')
            if not self._running:
                watcher.stop()
                break
            # resource_version '0' means getting a recent resource without
            # consistency guarantee, this is to reduce the load of etcd.
            # Ref: https://kubernetes.io/docs/reference/using-api
            # /api-concepts/ #the-resourceversion-parameter
            stream = watcher.stream(
                k8s_client.core.list_namespaced_pod,
                namespace=Envs.K8S_NAMESPACE,
                label_selector='app-name',
                resource_version=resource_version,
                _request_timeout=900,  # Sometimes watch gets stuck
            )

            try:
                for event in stream:
                    self._produce_event(event, ObjectType.POD)
                    metadata = event['object'].metadata
                    if metadata.resource_version is not None:
                        resource_version = max(metadata.resource_version,
                                               resource_version)
                        logging.debug(
                            f'resource_version now: {resource_version}')
            except client.exceptions.ApiException as e:
                logging.error(f'watcher:{str(e)}')
                if e.status == HTTPStatus.GONE:
                    # It has been too old, resources should be relisted
                    resource_version = '0'
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'K8s watcher gets event error: {str(e)}',
                              exc_info=True)


k8s_watcher = K8sWatcher()
