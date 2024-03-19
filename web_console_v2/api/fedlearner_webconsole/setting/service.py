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
import logging
import os
import json
from typing import List, Optional
from google.protobuf import text_format
from google.protobuf.json_format import MessageToDict, Parse, ParseDict, ParseError
from sqlalchemy.orm.session import Session
from envs import Envs
from fedlearner_webconsole.proto import setting_pb2
from fedlearner_webconsole.setting.models import Setting
from fedlearner_webconsole.proto.setting_pb2 import SystemVariables
from fedlearner_webconsole.utils.app_version import ApplicationVersion
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name
from fedlearner_webconsole.exceptions import InternalException


def parse_application_version(content: str) -> ApplicationVersion:
    revision, branch_name, version, pub_date = None, None, None, None
    for line in content.split('\n'):
        if line.find(':') == -1:
            continue
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()
        if value == '':
            continue
        if key == 'revision':
            revision = value
        elif key == 'branch name':
            branch_name = value
        elif key == 'version':
            version = value
        elif key == 'pub date':
            pub_date = value

    return ApplicationVersion(revision=revision, branch_name=branch_name, version=version, pub_date=pub_date)


class SettingService:

    def __init__(self, session: Session):
        self._session = session

    def get_setting(self, key: str) -> Optional[Setting]:
        return self._session.query(Setting).filter_by(uniq_key=key).first()

    def create_or_update_setting(self, key: str, value: str) -> Setting:
        setting = self._session.query(Setting).filter_by(uniq_key=key).first()
        if setting is None:
            setting = Setting(uniq_key=key, value=value)
            self._session.add(setting)
            self._session.commit()
        else:
            setting.value = value
            self._session.commit()
        return setting

    def get_system_variables(self) -> SystemVariables:
        result = SystemVariables()
        setting = self.get_setting('system_variables')
        if setting is None:
            return result
        text_format.Parse(setting.value, result)
        return result

    def set_system_variables(self, system_variables: SystemVariables):
        self.create_or_update_setting('system_variables', text_format.MessageToString(system_variables))

    @staticmethod
    def get_application_version() -> ApplicationVersion:
        application_version_path = os.path.join(Envs.BASE_DIR, '../current_revision')
        if not os.path.exists(application_version_path):
            content = ''
        else:
            with open(application_version_path, 'r', encoding='utf-8') as f:
                content = f.read()
        return parse_application_version(content)

    def get_namespace(self) -> str:
        return self.get_system_variables_dict().get('namespace', 'default')

    def get_system_variables_dict(self) -> dict:
        variables = self.get_system_variables().variables
        return {
            var.name: MessageToDict(var.value, preserving_proto_field_name=True, including_default_value_fields=True)
            for var in variables
        }

    @staticmethod
    def get_system_info() -> setting_pb2.SystemInfo:
        system_info: setting_pb2.SystemInfo = Parse(Envs.SYSTEM_INFO, setting_pb2.SystemInfo())
        system_info.pure_domain_name = get_pure_domain_name(system_info.domain_name) or ''
        return system_info


class DashboardService(object):
    # Reference: https://discuss.elastic.co/t/kibana-g-and-a-parameters-in-the-dashboards-url-string/264642
    DASHBOARD_FMT_STR = '{kibana_address}/app/kibana#/dashboard/{object_uuid}?_a=(filters:!((query:(match_phrase:(service.environment:{cluster})))))'  # pylint:disable=line-too-long

    REQUIRED_DASHBOARD = frozenset(['overview'])

    @staticmethod
    def _validate_saved_object_uuid(saved_object_uuid: str) -> bool:
        if not isinstance(saved_object_uuid, str) or not saved_object_uuid:
            return False
        return True

    def get_dashboards(self) -> List[setting_pb2.DashboardInformation]:
        dashboard_list = json.loads(Envs.KIBANA_DASHBOARD_LIST)
        if not DashboardService.REQUIRED_DASHBOARD.issubset({d['name'] for d in dashboard_list}):
            raise InternalException(
                f'failed to find required dashboard {list(DashboardService.REQUIRED_DASHBOARD)} uuid')
        try:
            dashboard_information_list = []
            for item in dashboard_list:
                dashboard_information = ParseDict(item, setting_pb2.DashboardInformation(), ignore_unknown_fields=False)
                if not self._validate_saved_object_uuid(dashboard_information.uuid):
                    raise InternalException(f'invalid uuid for dashboard {dashboard_information.name}')

                dashboard_information.url = DashboardService.DASHBOARD_FMT_STR.format(
                    kibana_address=Envs.KIBANA_ADDRESS, object_uuid=dashboard_information.uuid, cluster=Envs.CLUSTER)
                dashboard_information_list.append(dashboard_information)
            return dashboard_information_list
        except ParseError as err:
            msg = f'invalid `KIBANA_DASHBOARD_LIST`, details: {err}'
            logging.warning(msg)
            raise InternalException(msg) from err
