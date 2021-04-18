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
import os
import logging
import threading, queue
import traceback
from http import HTTPStatus
from kubernetes import client, watch, config
from fedlearner_webconsole.envs import Envs

FEDLEARNER_CUSTOM_GROUP = 'fedlearner.k8s.io'
FEDLEARNER_CUSTOM_VERSION = 'v1alpha1'


class K8sWatcher(object):
    def __init__(self, config_path=None):
        if config_path is None:
            config.load_incluster_config()
        else:
            config.load_kube_config(config_path)
        self._lock = threading.Lock()
        self._running = False
        self._api = client.CoreV1Api()
        self.crds = client.CustomObjectsApi()

        self._flapp_watch = watch.Watch()
        self._pods_watch = watch.Watch()
        self._flapp_watch_thread = None
        self._pods_watch_thread = None
        self._cache_consumer_thread = None

        # https://stackoverflow.com/questions/62223424/
        # simplequeue-vs-queue-in-python-what-is-the-advantage-of-using-simplequeue
        # put never block. only python 3.7
        # self._queue = queue.SimpleQueue()
        self._queue = queue.Queue()
        #  Python dictionary operations are thread-safe,
        #  so there's no need to 'lock' the dictionary when adding or deleting keys
        self._cache = {}

        self._flapp_cache_lock = threading.Lock()
        self._pods_cache_lock = threading.Lock()

    def start(self):
        if self._running:
            logging.warning('K8s watcher has already started')
        with self._lock:
            self._running = True
            self._flapp_watch_thread = threading.Thread(target=self._k8s_flapp_watcher,
                                                        name='flapp_watcher')
            self._pods_watch_thread = threading.Thread(target=self._k8s_pods_watch,
                                                       name='pods_watcher')
            self._cache_consumer_thread = threading.Thread(target=self.event_consumer,
                                                           name='cache_consumer')
            self._flapp_watch_thread.daemon = True
            self._pods_watch_thread.daemon = True
            self._cache_consumer_thread.daemon = True
            self._pods_watch_thread.start()
            self._flapp_watch_thread.start()
            self._cache_consumer_thread.start()
            logging.error('K8s watcher started')

    def get_cache(self, flapp_name):
        if flapp_name in self._cache:
            return self._cache[flapp_name]
        return {'flapp': None, 'pods': {'items': []}}

    def event_consumer(self):
        while True:
            event = self._queue.get()
            flapp_name = event['flapp_name']
            if flapp_name not in self._cache:
                self._cache[flapp_name] = {'pods': {'items': []},
                                           'deleted': False}
            if event['is_flapp']:
                if event['event_type'] == 'DELETED':
                    self._cache[flapp_name] = {'pods': {'items': []},
                                               'deleted': True}
                else:
                    self._cache[flapp_name]['deleted'] = False
                    self._cache[flapp_name]['flapp'] = event['flapp']
            else:
                print(flapp_name)
                if self._cache[flapp_name]['deleted']:
                    continue
                dup_index = None
                for index, pod in enumerate(self._cache[flapp_name]['pods']['items']):
                    if pod['metadata']['name'] == event['pod']['metadata']['name']:
                        dup_index = index
                        break
                if dup_index:
                    del self._cache[flapp_name]['pods']['items'][dup_index]
                self._cache[flapp_name]['pods']['items'].append(event['pod'])

            try:
                print(self._cache[flapp_name])
            except Exception:
                pass

    def _k8s_flapp_watcher(self):
        # init cache for flapp
        resource_version = '0'
        while True:
            if not self._running:
                break
            stream = self._flapp_watch.stream(self.crds.list_namespaced_custom_object,
                                              group=FEDLEARNER_CUSTOM_GROUP,
                                              version=FEDLEARNER_CUSTOM_VERSION,
                                              namespace=Envs.NAMESPACE,
                                              plural='flapps',
                                              resource_version=resource_version
                                              )
            try:
                for event in stream:
                    event_type = event["type"]
                    obj = event["object"]
                    metadata = obj.get('metadata')
                    status = obj.get('status')
                    # put event to queue
                    self._queue.put({'flapp_name': metadata['name'],
                                     # ADDED DELETED MODIFIED
                                     'event_type': event_type,
                                     'is_flapp': True,
                                     'flapp': {'status': status}})
                    if not self._running:
                        self._flapp_watch.stop()
                        self._pods_watch.stop()
                        break
            except client.exceptions.ApiException as e:
                logging.error(f'watcher:{str(e)}')
                if e.status == 410:
                    resource_version = '0'
            except Exception as e:
                logging.error(f'K8s watcher gets event error: {str(e)}')
                logging.error(traceback.format_exc())

    def _k8s_pods_watch(self):
        # init cache for flapp
        resource_version = '0'
        while True:
            if not self._running:
                break
            stream = self._pods_watch.stream(self._api.list_namespaced_pod,
                                             namespace=Envs.NAMESPACE,
                                             label_selector='app-name',
                                             resource_version=resource_version)

            try:
                for event in stream:
                    event_type = event["type"]
                    obj = event["object"]
                    obj = obj.to_dict()
                    metadata = obj.get('metadata')
                    status = obj.get('status')
                    self._queue.put({'flapp_name': metadata['labels']['app-name'],
                                     # ADDED DELETED MODIFIED
                                     'event_type': event_type,
                                     'is_flapp': False,
                                     'pod': {'status': status,
                                             'metadata': metadata
                                             }
                                     })

                    if metadata['resource_version'] is not None:
                        resource_version = metadata['resource_version']
                        logging.debug('resource_version now: {0}'.format(resource_version))
                    if not self._running:
                        self._flapp_watch.stop()
                        self._pods_watch.stop()
                        break
            except client.exceptions.ApiException as e:
                logging.error(f'watcher:{str(e)}')
                if e.status == 410:
                    resource_version = '0'
            except Exception as e:
                logging.error(f'K8s watcher gets event error: {str(e)}')
                logging.error(traceback.format_exc())


k8s_watcher = K8sWatcher(os.environ.get('K8S_CONFIG_PATH', None))
