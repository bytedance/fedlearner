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
import json
import logging
import os
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from google.protobuf.struct_pb2 import Value

from envs import Envs
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.setting_pb2 import DashboardInformation, SystemVariables, SystemVariable, SystemInfo
from fedlearner_webconsole.setting.apis import _POD_NAMESPACE
from fedlearner_webconsole.setting.models import Setting
from fedlearner_webconsole.setting.service import SettingService

from testing.common import BaseTestCase


class SettingApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            setting = Setting(uniq_key='key1', value='value 1')
            session.add(setting)
            session.commit()

    @patch('fedlearner_webconsole.setting.apis.k8s_client')
    def test_get_webconsole_image(self, mock_k8s_client: MagicMock):
        deployment = SimpleNamespace(
            **{
                'metadata':
                    SimpleNamespace(**{
                        'name': 'fedlearner-web-console-v2',
                        'namespace': 'testns'
                    }),
                'spec':
                    SimpleNamespace(
                        **{
                            'template':
                                SimpleNamespace(
                                    **{
                                        'spec':
                                            SimpleNamespace(
                                                **{'containers': [SimpleNamespace(**{'image': 'fedlearner:test'})]})
                                    })
                        })
            })
        mock_k8s_client.get_deployment = MagicMock(return_value=deployment)
        resp = self.get_helper('/api/v2/settings/webconsole_image')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.signin_as_admin()
        resp = self.get_helper('/api/v2/settings/webconsole_image')
        self.assertResponseDataEqual(resp, {
            'uniq_key': 'webconsole_image',
            'value': 'fedlearner:test',
        })

    def test_get_system_variables(self):
        system_variables = SystemVariables(variables=[
            SystemVariable(name='test1', value_type=SystemVariable.ValueType.INT, value=Value(number_value=1))
        ])
        with db.session_scope() as session:
            SettingService(session).set_system_variables(system_variables)
            session.commit()
        resp = self.get_helper('/api/v2/settings/system_variables')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.signin_as_admin()
        resp = self.get_helper('/api/v2/settings/system_variables')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            resp, {'variables': [{
                'name': 'test1',
                'value': 1.0,
                'value_type': 'INT',
                'fixed': False
            }]})

    def test_get(self):
        resp = self.get_helper('/api/v2/settings/key1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp)['value'], 'value 1')
        # Black list one
        resp = self.get_helper('/api/v2/settings/variables')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        resp = self.get_helper('/api/v2/settings/key2')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_put(self):
        resp = self.put_helper('/api/v2/settings/key1', data={'value': 'new value'})
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.signin_as_admin()
        resp = self.put_helper('/api/v2/settings/key1', data={'value': 'new value'})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp)['value'], 'new value')
        with db.session_scope() as session:
            setting = session.query(Setting).filter_by(uniq_key='key1').first()
            self.assertEqual(setting.value, 'new value')
        # Black list one
        resp = self.put_helper('/api/v2/settings/system_variables', data={'value': 'new value'})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)


class SettingsApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        self._system_pods = SimpleNamespace(
            **{
                'items': [
                    SimpleNamespace(**{'metadata': SimpleNamespace(**{'name': 'fake-fedlearner-web-console-v2-1'})}),
                    SimpleNamespace(**{'metadata': SimpleNamespace(**{'name': 'fake-fedlearner-web-console-v2-2'})}),
                ]
            })
        self._system_pod_log = 'log1\nlog2'
        self._mock_k8s_client = MagicMock()
        self._mock_k8s_client.get_pods = MagicMock(return_value=self._system_pods)
        self._mock_k8s_client.get_pod_log = MagicMock(return_value=self._system_pod_log)
        self.signin_as_admin()

    def test_get_system_pods(self):
        with patch('fedlearner_webconsole.setting.apis.k8s_client', self._mock_k8s_client):
            resp = self.get_helper('/api/v2/system_pods/name')
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            self.assertEqual(self.get_response_data(resp),
                             ['fake-fedlearner-web-console-v2-1', 'fake-fedlearner-web-console-v2-2'])

    def test_get_system_pods_log(self):
        fake_pod_name = 'fake-fedlearner-web-console-v2-1'
        with patch('fedlearner_webconsole.setting.apis.k8s_client', self._mock_k8s_client):
            resp = self.get_helper(f'/api/v2/system_pods/{fake_pod_name}/logs?tail_lines=100')
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            self.assertEqual(self.get_response_data(resp), ['log1', 'log2'])
            self._mock_k8s_client.get_pod_log.assert_called_with(name=fake_pod_name,
                                                                 namespace=_POD_NAMESPACE,
                                                                 tail_lines=100)

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(name='hahaha', domain_name='fl-test.com', pure_domain_name='test'))
    def test_get_own_info_api(self):
        resp = self.get_helper('/api/v2/settings/system_info')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'name': 'hahaha', 'domain_name': 'fl-test.com', 'pure_domain_name': 'test'})


class UpdateSystemVariablesApi(BaseTestCase):

    def test_post_no_permission(self):
        resp = self.post_helper('/api/v2/settings:update_system_variables', data={'variables': []})
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

    def test_post_invalid_argument(self):
        system_variables = SystemVariables(variables=[
            SystemVariable(name='test1', value_type=SystemVariable.ValueType.INT, value=Value(number_value=1))
        ])
        with db.session_scope() as session:
            SettingService(session).set_system_variables(system_variables)
            session.commit()

        self.signin_as_admin()
        resp = self.post_helper('/api/v2/settings:update_system_variables', data={'variables': [{'h': 'ff'}]})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('Failed to parse variables field', json.loads(resp.data).get('details'))

        with db.session_scope() as session:
            self.assertEqual(system_variables, SettingService(session).get_system_variables())

    def test_post_200(self):
        self.signin_as_admin()
        resp = self.post_helper('/api/v2/settings:update_system_variables',
                                data={'variables': [{
                                    'name': 'new_var',
                                    'value': 2,
                                    'value_type': 'INT'
                                }]})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            resp, {'variables': [{
                'name': 'new_var',
                'value': 2.0,
                'value_type': 'INT',
                'fixed': False
            }]})

        expected_system_variables = SystemVariables(variables=[
            SystemVariable(name='new_var', value_type=SystemVariable.ValueType.INT, value=Value(number_value=2))
        ])
        with db.session_scope() as session:
            self.assertEqual(expected_system_variables, SettingService(session).get_system_variables())


class UpdateImageApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    @patch('fedlearner_webconsole.setting.apis.k8s_client')
    def test_post(self, mock_k8s_client: MagicMock):
        deployment = SimpleNamespace(
            **{
                'metadata':
                    SimpleNamespace(**{
                        'name': 'fedlearner-web-console-v2',
                        'namespace': 'testns'
                    }),
                'spec':
                    SimpleNamespace(
                        **{
                            'template':
                                SimpleNamespace(
                                    **{
                                        'spec':
                                            SimpleNamespace(
                                                **{'containers': [SimpleNamespace(**{'image': 'fedlearner:test'})]})
                                    })
                        })
            })
        mock_k8s_client.get_deployment = MagicMock(return_value=deployment)
        mock_k8s_client.create_or_update_deployment = MagicMock()

        resp = self.post_helper('/api/v2/settings:update_image', data={'webconsole_image': 'test-new-image'})
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

        self.signin_as_admin()
        resp = self.post_helper('/api/v2/settings:update_image', data={'webconsole_image': 'test-new-image'})
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        _, kwargs = mock_k8s_client.create_or_update_deployment.call_args
        self.assertEqual(kwargs['spec'].template.spec.containers[0].image, 'test-new-image')
        self.assertEqual(kwargs['name'], deployment.metadata.name)
        self.assertEqual(kwargs['namespace'], deployment.metadata.namespace)


class VersionsApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def test_get_version_api(self):
        resp = self.get_helper('/api/v2/versions')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp)['branch_name'], '')

        content = """
        revision:f09d681b4eda01f053cc1a645fa6fc0775852a48
        branch name:release-2.0.1
        version:2.0.1.5
        pub date:Fri Jul 16 12:23:19 CST 2021
        """
        application_version_path = os.path.join(Envs.BASE_DIR, '../current_revision')
        with open(application_version_path, 'wt', encoding='utf-8') as f:
            f.write(content)

        resp = self.get_helper('/api/v2/versions')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            resp, {
                'pub_date': 'Fri Jul 16 12:23:19 CST 2021',
                'revision': 'f09d681b4eda01f053cc1a645fa6fc0775852a48',
                'branch_name': 'release-2.0.1',
                'version': '2.0.1.5',
            })

        os.remove(application_version_path)


class DashboardsApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def test_get_flag_disable(self):
        self.signin_as_admin()
        get_dashboard_response = self.get_helper('/api/v2/dashboards')
        self.assertEqual(get_dashboard_response.status_code, HTTPStatus.FORBIDDEN)

    @patch('fedlearner_webconsole.flag.models.Flag.DASHBOARD_ENABLED.value', True)
    @patch('fedlearner_webconsole.setting.apis.DashboardService.get_dashboards')
    def test_get(self, mock_get_dashboards: MagicMock):
        mock_get_dashboards.return_value = [DashboardInformation()]
        get_dashboard_response = self.get_helper('/api/v2/dashboards')
        self.assertEqual(get_dashboard_response.status_code, HTTPStatus.UNAUTHORIZED)

        mock_get_dashboards.reset_mock()
        self.signin_as_admin()
        mock_get_dashboards.return_value = [DashboardInformation()]
        get_dashboard_response = self.get_helper('/api/v2/dashboards')
        self.assertEqual(get_dashboard_response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(get_dashboard_response, [{'name': '', 'uuid': '', 'url': ''}])

        mock_get_dashboards.reset_mock()
        mock_get_dashboards.side_effect = InternalException('')
        get_dashboard_response = self.get_helper('/api/v2/dashboards')
        self.assertEqual(get_dashboard_response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
