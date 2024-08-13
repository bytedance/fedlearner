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
import unittest
from http import HTTPStatus
from unittest.mock import patch

import jwt
from flask import g
from datetime import timedelta
from config import Config
from envs import Envs
from testing.common import BaseTestCase
from testing.helpers import FakeResponse
from fedlearner_webconsole.auth.services import SessionService
from fedlearner_webconsole.auth.third_party_sso import credentials_required, \
    get_user_info_with_cache, SsoInfos, JwtHandler
from fedlearner_webconsole.exceptions import UnauthorizedException
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.pp_datetime import now


@credentials_required
def test_some_api():
    return 1


class OauthHandlerTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            session.add(User(username='test'))
            session.commit()
        with open(f'{Envs.BASE_DIR}/testing/test_data/test_sso.json', encoding='utf-8') as f:
            self.patch_ssoinfos = patch('fedlearner_webconsole.auth.third_party_sso.Envs.SSO_INFOS', f.read())
            self.patch_ssoinfos.start()
            self.fake_sso_info_manager = SsoInfos()
            self.patch_manager = patch('fedlearner_webconsole.auth.third_party_sso.sso_info_manager',
                                       self.fake_sso_info_manager)
            self.patch_manager.start()

    def tearDown(self):
        self.patch_manager.stop()
        self.patch_ssoinfos.stop()
        # clear cache to isolate the cache of each test case.
        get_user_info_with_cache.cache_clear()
        super().tearDown()

    def test_get_sso_infos(self):
        self.assertEqual(len(self.fake_sso_info_manager.sso_infos), 2)

    def test_get_sso_info(self,):
        self.assertEqual(self.fake_sso_info_manager.get_sso_info('test').name, 'test')
        self.assertEqual(self.fake_sso_info_manager.get_sso_info('test').display_name, 'test')

    @patch('fedlearner_webconsole.auth.third_party_sso.requests.get')
    @patch('fedlearner_webconsole.auth.third_party_sso.request.headers.get')
    def test_credentials_required(self, mock_headers, mock_request_get):
        # test not supported sso
        mock_headers.return_value = 'not_supported_sso oauth access_token'
        self.assertRaises(UnauthorizedException, test_some_api)
        mock_request_get.return_value = FakeResponse({'username': 'test', 'email': 'test'}, HTTPStatus.OK)
        self.assertRaises(UnauthorizedException, test_some_api)

        # test supported sso
        mock_headers.return_value = 'test oauth access_token'
        test_some_api()

    @patch('fedlearner_webconsole.auth.third_party_sso.requests.get')
    @patch('fedlearner_webconsole.auth.third_party_sso.request.headers.get')
    def test_get_user_info_cache(self, mock_headers, mock_request_get):
        mock_headers.return_value = 'test oauth access_token'
        mock_request_get.return_value = FakeResponse({'username': 'test', 'email': 'test'}, HTTPStatus.OK)
        test_some_api()
        test_some_api()
        mock_request_get.assert_called_once()
        mock_headers.return_value = 'test oauth access_token1'
        mock_request_get.return_value = FakeResponse({'data': {'username': 'test', 'email': 'test'}}, HTTPStatus.OK)
        test_some_api()
        test_some_api()
        self.assertEqual(mock_request_get.call_count, 2)


class JwtHandlerTest(BaseTestCase):

    def test_check_credentials(self):
        jwt_handler = JwtHandler()
        self.assertEqual(jwt_handler.check_credentials(self._token), 'ada')
        jti = jwt.decode(self._token, key=Config.JWT_SECRET_KEY, algorithms='HS256').get('jti')
        with db.session_scope() as session:
            session_obj = SessionService(session).get_session_by_jti(jti)
            SessionService(session).delete_session(session_obj=session_obj)
            session.commit()
        self.assertRaises(UnauthorizedException, jwt_handler.check_credentials, self._token)
        self.signin_as_admin()
        with patch('fedlearner_webconsole.auth.third_party_sso.now') as fake_now:
            fake_now.return_value = now() + timedelta(seconds=86405)
            self.assertRaises(UnauthorizedException, jwt_handler.check_credentials, self._token)

    def test_signout(self):
        jwt_handler = JwtHandler()
        jti = jwt.decode(self._token, key=Config.JWT_SECRET_KEY, algorithms='HS256').get('jti')
        with db.session_scope() as session:
            session_obj = SessionService(session).get_session_by_jti(jti)
        self.assertIsNotNone(session_obj)
        g.jti = jti
        jwt_handler.signout()
        with db.session_scope() as session:
            session_obj = SessionService(session).get_session_by_jti(jti)
        self.assertIsNone(session_obj)


class CasHandlerTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            session.add(User(username='test'))
            session.commit()
        with open(f'{Envs.BASE_DIR}/testing/test_data/test_sso.json', encoding='utf-8') as f:
            self.patch_ssoinfos = patch('fedlearner_webconsole.auth.third_party_sso.Envs.SSO_INFOS', f.read())
            self.patch_ssoinfos.start()
            self.fake_sso_info_manager = SsoInfos()
            self.patch_manager = patch('fedlearner_webconsole.auth.third_party_sso.sso_info_manager',
                                       self.fake_sso_info_manager)
            self.patch_manager.start()

    def tearDown(self):
        self.patch_manager.stop()
        self.patch_ssoinfos.stop()
        super().tearDown()

    @patch('fedlearner_webconsole.auth.third_party_sso.requests.get')
    @patch('fedlearner_webconsole.auth.third_party_sso.request.headers.get')
    def test_credentials_required_cas(self, mock_headers, mock_request_get):
        mock_request_get.return_value = FakeResponse({'username': 'test', 'email': 'test'}, HTTPStatus.OK)
        # test supported sso
        mock_headers.return_value = f'test_cas cas {self._token}'
        test_some_api()
        mock_headers.return_value = f'test_cas cas {self._token}aa'
        self.assertRaises(UnauthorizedException, test_some_api)


if __name__ == '__main__':
    unittest.main()
