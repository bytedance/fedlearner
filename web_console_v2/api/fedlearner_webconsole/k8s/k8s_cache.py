# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from enum import Enum

from fedlearner_webconsole.k8s.models import get_app_name_from_metadata


class EventType(Enum):
    ADDED = 'ADDED'
    MODIFIED = 'MODIFIED'
    DELETED = 'DELETED'


class ObjectType(Enum):
    POD = 'POD'
    FLAPP = 'FLAPP'
    SPARKAPP = 'SPARKAPP'
    FEDAPP = 'FEDAPP'


class Event(object):

    def __init__(self, app_name: str, event_type: EventType, obj_type: ObjectType, obj_dict: dict):
        self.app_name = app_name
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
            app_name = get_app_name_from_metadata(obj.metadata)
            obj = obj.to_dict()
            status = obj.get('status')
            return Event(app_name,
                         EventType(event_type),
                         obj_type,
                         obj_dict={
                             'status': status,
                             'metadata': obj.get('metadata', {})
                         })

        metadata = obj.get('metadata', {})
        # put event to queue
        return Event(metadata.get('name', None), EventType(event_type), obj_type, obj_dict=obj)


class K8sCache(object):

    def __init__(self):
        # key: app_name, value: a dict
        # {'flapp': flapp cache, 'pods': pods cache,
        #                        'deleted': is flapp deleted}
        self._cache = {}
        self._pod_cache = {}

    def inspect(self) -> dict:
        c = {}
        c['pod_cache'] = self._pod_cache
        c['app_cache'] = self._cache
        return c

    def update_cache(self, event: Event):
        if event.obj_type == ObjectType.POD:
            self._updata_pod_cache(event)
        else:
            self._update_app_cache(event)

    def get_cache(self, app_name: str) -> dict:
        return self._get_app_cache(app_name)

    def _update_app_cache(self, event: Event):
        app_name = event.app_name

        self._cache[app_name] = {'app': event.obj_dict}
        if app_name not in self._pod_cache:
            self._pod_cache[app_name] = {'items': [], 'deleted': False}
        self._pod_cache[app_name]['deleted'] = False
        if event.event_type == EventType.DELETED:
            self._cache[app_name] = {'app': None}
            self._pod_cache[app_name] = {'items': [], 'deleted': True}

    def _get_app_cache(self, app_name) -> dict:
        if app_name not in self._cache:
            return {'app': None, 'pods': {'items': []}}
        app = {**self._cache[app_name], 'pods': self._pod_cache[app_name]}
        return app

    def _updata_pod_cache(self, event: Event):
        app_name = event.app_name
        if app_name not in self._pod_cache:
            self._pod_cache[app_name] = {'items': [], 'deleted': False}
        if self._pod_cache[app_name]['deleted']:
            return
        existed = False
        for index, pod in enumerate(self._pod_cache[app_name]['items']):
            if pod['metadata']['name'] == event.obj_dict['metadata']['name']:
                existed = True
                self._pod_cache[app_name]['items'][index] = event.obj_dict
                break
        if not existed:
            self._pod_cache[app_name]['items'].append(event.obj_dict)


k8s_cache = K8sCache()
