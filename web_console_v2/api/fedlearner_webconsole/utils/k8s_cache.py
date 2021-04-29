# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import threading
from enum import Enum


class EventType(Enum):
    ADDED = 'ADDED'
    MODIFIED = 'MODIFIED'
    DELETED = 'DELETED'


class ObjectType(Enum):
    POD = 'POD'
    FLAPP = 'FLAPP'


class Event(object):
    def __init__(self, flapp_name, event_type, obj_type, obj_dict):
        self.flapp_name = flapp_name
        self.event_type = event_type
        self.obj_type = obj_type
        # {'status': {}, 'metadata': {}}
        self.obj_dict = obj_dict

    @staticmethod
    def from_json(event, obj_type):
        # TODO(xiangyuxuan): move this to k8s/models.py
        event_type = event['type']
        obj = event['object']
        if obj_type == ObjectType.POD:
            obj = obj.to_dict()
            metadata = obj.get('metadata')
            status = obj.get('status')
            flapp_name = metadata['labels']['app-name']
            return Event(flapp_name,
                         EventType(event_type),
                         obj_type,
                         obj_dict={'status': status,
                                   'metadata': metadata})
        metadata = obj.get('metadata')
        status = obj.get('status')
        # put event to queue
        return Event(metadata['name'],
                     EventType(event_type),
                     obj_type,
                     obj_dict={'status': status})


class K8sCache(object):

    def __init__(self):
        self._lock = threading.Lock()
        # key: flapp_name, value: a dict
        # {'flapp': flapp cache, 'pods': pods cache,
        #                        'deleted': is flapp deleted}
        self._cache = {}

    # TODO(xiangyuxuan): use class instead of json to manage cache and queue
    def update_cache(self, event: Event):
        with self._lock:
            flapp_name = event.flapp_name
            if flapp_name not in self._cache:
                self._cache[flapp_name] = {'pods': {'items': []},
                                           'deleted': False}
            # if not flapp's then pod's event
            if event.obj_type == ObjectType.FLAPP:
                if event.event_type == EventType.DELETED:
                    self._cache[flapp_name] = {'pods': {'items': []},
                                               'deleted': True}
                else:
                    self._cache[flapp_name]['deleted'] = False
                    self._cache[flapp_name]['flapp'] = event.obj_dict
            else:
                if self._cache[flapp_name]['deleted']:
                    return
                existed = False
                for index, pod in enumerate(
                        self._cache[flapp_name]['pods']['items']):
                    if pod['metadata']['name'] == \
                            event.obj_dict['metadata']['name']:
                        existed = True
                        self._cache[flapp_name]['pods']['items'][index] \
                            = event.obj_dict
                        break
                if not existed:
                    self._cache[flapp_name]['pods'][
                        'items'].append(event.obj_dict)

    def get_cache(self, flapp_name):
        # use read-write lock to fast
        with self._lock:
            if flapp_name in self._cache:
                return self._cache[flapp_name]
        return {'flapp': None, 'pods': {'items': []}}


k8s_cache = K8sCache()
