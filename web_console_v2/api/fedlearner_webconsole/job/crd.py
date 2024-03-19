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

import logging
from typing import Optional

from fedlearner_webconsole.k8s.k8s_cache import k8s_cache
from fedlearner_webconsole.k8s.models import CrdKind, SparkApp, FlApp, FedApp, UnknownCrd
from fedlearner_webconsole.k8s.k8s_client import k8s_client
from fedlearner_webconsole.utils.metrics import emit_store

CRD_CLASS_MAP = {
    CrdKind.FLAPP: FlApp,
    CrdKind.SPARKAPPLICATION: SparkApp,
    CrdKind.FEDAPP: FedApp,
    CrdKind.UNKNOWN: UnknownCrd
}


class CrdService(object):

    def __init__(self, kind: str, api_version: str, app_name: str):
        self.kind = kind
        # only un-UNKNOWN kind crd support complete/failed/pods detail
        # UNKNOWN only support create and delete
        self.supported_kind = CrdKind.from_value(kind)
        self.api_version = api_version
        self.plural = f'{kind.lower()}s'
        self.group, _, self.version = api_version.partition('/')
        self.app_name = app_name

    def get_k8s_app(self, snapshot: Optional[dict]):
        if snapshot is None:
            snapshot = self.get_k8s_app_cache()
        return CRD_CLASS_MAP[self.supported_kind].from_json(snapshot)

    def delete_app(self):
        emit_store('job.crd_service.deletion', value=1, tags={'name': self.app_name, 'plural': self.plural})
        k8s_client.delete_app(self.app_name, self.group, self.version, self.plural)

    def create_app(self, yaml: dict):
        emit_store('job.crd_service.submission', value=1, tags={'name': self.app_name, 'plural': self.plural})
        k8s_client.create_app(yaml, self.group, self.version, self.plural)

    def get_k8s_app_cache(self):
        if self.supported_kind == CrdKind.UNKNOWN:
            try:
                return {'app': k8s_client.get_custom_object(self.app_name, self.group, self.version, self.plural)}
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'Get app detail failed: {str(e)}')
                return {'app': {}}
        return k8s_cache.get_cache(self.app_name)
