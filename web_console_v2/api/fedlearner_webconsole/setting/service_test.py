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
# pylint: disable=protected-access
import json
import unittest
from unittest.mock import patch

from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.initial_db import initial_db
from fedlearner_webconsole.proto.setting_pb2 import DashboardInformation, SystemInfo, SystemVariables
from fedlearner_webconsole.setting.models import Setting
from fedlearner_webconsole.setting.service import DashboardService, parse_application_version, SettingService
from fedlearner_webconsole.utils.app_version import Version
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import InternalException

from testing.no_web_server_test_case import NoWebServerTestCase


class ServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        initial_db()

    def test_get_setting(self):
        with db.session_scope() as session:
            setting = Setting(uniq_key='test_key1', value='test value 1')
            session.add(setting)
            session.commit()
        # A new session
        with db.session_scope() as session:
            setting = SettingService(session).get_setting('test_key1')
            self.assertEqual(setting.value, 'test value 1')
            setting = SettingService(session).get_setting('100')
            self.assertIsNone(setting)

    def test_set_setting(self):
        # A new setting
        with db.session_scope() as session:
            setting = SettingService(session).create_or_update_setting(key='k1', value='v1')
            self.assertEqual(setting.uniq_key, 'k1')
            self.assertEqual(setting.value, 'v1')
            setting_in_db = \
                session.query(Setting).filter_by(uniq_key='k1').first()
            self.assertEqual(setting_in_db.value, 'v1')
        # Existing setting
        with db.session_scope() as session:
            SettingService(session).create_or_update_setting(key='k1', value='v2')
            setting_in_db = \
                session.query(Setting).filter_by(uniq_key='k1').first()
            self.assertEqual(setting_in_db.value, 'v2')

    def test_parse_application_version(self):
        content = """
        revision:f09d681b4eda01f053cc1a645fa6fc0775852a48
        branch name:release-2.0.1
        version:2.0.1.5
        pub date:Fri Jul 16 12:23:19 CST 2021
        """
        application_version = parse_application_version(content)
        self.assertEqual(application_version.revision, 'f09d681b4eda01f053cc1a645fa6fc0775852a48')
        self.assertEqual(application_version.branch_name, 'release-2.0.1')
        self.assertEqual(application_version.version, Version('2.0.1.5'))
        self.assertEqual(application_version.pub_date, 'Fri Jul 16 12:23:19 CST 2021')

        content = """
        revision:f09d681b4eda01f053cc1a645fa6fc0775852a48
        branch name:master
        version:
        pub date:Fri Jul 16 12:23:19 CST 2021
        """
        application_version = parse_application_version(content)
        self.assertEqual(application_version.revision, 'f09d681b4eda01f053cc1a645fa6fc0775852a48')
        self.assertEqual(application_version.branch_name, 'master')
        self.assertIsNone(application_version.version.version)
        self.assertEqual(application_version.pub_date, 'Fri Jul 16 12:23:19 CST 2021')

    def test_get_variable_by_key(self):
        with db.session_scope() as session:
            self.assertEqual(SettingService(session).get_system_variables_dict()['namespace'], 'default')
            self.assertIsNone(SettingService(session).get_system_variables_dict().get('not-existed'))

    def test_get_system_variables_dict(self):
        test_data = {'variables': [{'name': 'a', 'value': 2}, {'name': 'b', 'value': []}]}
        with db.session_scope() as session:
            SettingService(session).set_system_variables(ParseDict(test_data, SystemVariables()))
            self.assertEqual(SettingService(session).get_system_variables_dict(), {'a': 2, 'b': []})

    @patch('envs.Envs.SYSTEM_INFO',
           json.dumps({
               'name': 'hahaha',
               'domain_name': 'fl-test.com',
               'pure_domain_name': 'test'
           }))
    def test_get_system_info(self):
        with db.session_scope() as session:
            system_info = SettingService(session).get_system_info()
            self.assertEqual(system_info, SystemInfo(name='hahaha', domain_name='fl-test.com', pure_domain_name='test'))


class DashboardServiceTest(unittest.TestCase):

    def test_validate_saved_object_uuid(self):
        self.assertFalse(DashboardService._validate_saved_object_uuid(''))
        self.assertFalse(DashboardService._validate_saved_object_uuid(None))
        self.assertFalse(DashboardService._validate_saved_object_uuid(1))
        self.assertTrue(DashboardService._validate_saved_object_uuid('c4c0af20-d03c-11ec-9be6-d5c22c92cd59'))

    def test_get_dashboards(self):
        with patch('envs.Envs.KIBANA_DASHBOARD_LIST', '[]'):
            with self.assertRaises(InternalException) as cm:
                DashboardService().get_dashboards()
            self.assertEqual(cm.exception.details, 'failed to find required dashboard [\'overview\'] uuid')
        with patch('envs.Envs.KIBANA_DASHBOARD_LIST', json.dumps([{'name': 'overview', 'uuid': 1}])):
            with self.assertRaises(InternalException) as cm:
                DashboardService().get_dashboards()
            self.assertEqual(
                cm.exception.details, 'invalid `KIBANA_DASHBOARD_LIST`, '
                'details: Failed to parse uuid field: expected string or bytes-like object.')
        with patch('envs.Envs.KIBANA_DASHBOARD_LIST', json.dumps([{'name': 'overview', 'test': 1}])):
            with self.assertRaises(InternalException) as cm:
                DashboardService().get_dashboards()
            self.assertIn(
                'invalid `KIBANA_DASHBOARD_LIST`, details: Message type "fedlearner_webconsole.proto.DashboardInformation" has no field named "test".',  # pylint: disable=line-too-long
                cm.exception.details)
        with patch('envs.Envs.KIBANA_DASHBOARD_LIST', json.dumps([{'name': 'overview', 'uuid': '1'}])):
            self.assertEqual(
                DashboardService().get_dashboards(),
                [
                    DashboardInformation(
                        name='overview',
                        uuid='1',
                        # pylint: disable=line-too-long
                        url=
                        'localhost:1993/app/kibana#/dashboard/1?_a=(filters:!((query:(match_phrase:(service.environment:default)))))',
                    )
                ])


if __name__ == '__main__':
    unittest.main()
