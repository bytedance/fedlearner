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
import json
import unittest
from http import HTTPStatus
from unittest.mock import patch
from datetime import timedelta

from testing.common import BaseTestCase
from testing.helpers import FakeResponse
from fedlearner_webconsole.auth.services import UserService
from fedlearner_webconsole.utils.pp_base64 import base64encode
from fedlearner_webconsole.utils.const import API_VERSION
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.auth.models import State, User
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.auth_pb2 import Sso, OAuthProtocol, CasProtocol
from fedlearner_webconsole.auth.third_party_sso import get_user_info_with_cache, SsoInfos, OAuthHandler, CasHandler
from fedlearner_webconsole.auth.models import Session as SessionTbl
from envs import Envs


class UsersApiTest(BaseTestCase):

    def test_get_all_users(self):
        deleted_user = User(username='deleted_one', email='who.knows@hhh.com', state=State.DELETED)
        with db.session_scope() as session:
            session.add(deleted_user)
            session.commit()

        resp = self.get_helper('/api/v2/auth/users')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

        self.signin_as_admin()

        resp = self.get_helper('/api/v2/auth/users')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(len(self.get_response_data(resp)), 3)

    def test_create_new_user(self):
        new_user = {
            'username': 'fedlearner',
            'password': 'fedlearner',
            'email': 'hello@bytedance.com',
            'role': 'USER',
            'name': 'codemonkey',
        }
        resp = self.post_helper('/api/v2/auth/users', data=new_user)
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

        self.signin_as_admin()
        illegal_cases = [
            'aaaaaaaa', '11111111', '!@#$%^[]', 'aaaA1111', 'AAAa!@#$', '1111!@#-', 'aa11!@', 'fl@123.',
            'fl@1234567890abcdefg.'
        ]
        legal_case = 'fl@1234.'

        for case in illegal_cases:
            new_user['password'] = base64encode(case)
            resp = self.post_helper('/api/v2/auth/users', data=new_user)
            print(self.get_response_data(resp))
            self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        new_user['password'] = base64encode(legal_case)
        resp = self.post_helper('/api/v2/auth/users', data=new_user)
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        self.assertEqual(self.get_response_data(resp).get('username'), 'fedlearner')

        # test_repeat_create
        resp = self.post_helper('/api/v2/auth/users', data=new_user)
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)


class AuthApiTest(BaseTestCase):

    def test_partial_update_user_info(self):
        self.signin_as_admin()
        resp = self.get_helper('/api/v2/auth/users')
        resp_data = self.get_response_data(resp)
        user_id = resp_data[0]['id']
        admin_id = resp_data[1]['id']

        self.signin_helper()
        resp = self.patch_helper('/api/v2/auth/users/10', data={})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

        resp = self.patch_helper(f'/api/v2/auth/users/{user_id}', data={
            'email': 'a_new_email@bytedance.com',
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp).get('email'), 'a_new_email@bytedance.com')

        resp = self.patch_helper(f'/api/v2/auth/users/{admin_id}', data={
            'name': 'cannot_modify',
        })
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

        # now we are signing in as admin
        self.signin_as_admin()
        resp = self.patch_helper(f'/api/v2/auth/users/{user_id}', data={
            'role': 'ADMIN',
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp).get('role'), 'ADMIN')

        resp = self.patch_helper(f'/api/v2/auth/users/{user_id}', data={
            'password': base64encode('fl@1234.'),
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)

    def test_delete_user(self):
        self.signin_as_admin()
        resp = self.get_helper('/api/v2/auth/users')
        resp_data = self.get_response_data(resp)
        user_id = resp_data[0]['id']
        admin_id = resp_data[1]['id']

        self.signin_helper()
        resp = self.delete_helper(url=f'/api/v2/auth/users/{user_id}')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

        self.signin_as_admin()

        resp = self.delete_helper(url=f'/api/v2/auth/users/{admin_id}')
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        resp = self.delete_helper(url=f'/api/v2/auth/users/{user_id}')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp).get('username'), 'ada')

    def test_get_specific_user(self):
        resp = self.get_helper(url='/api/v2/auth/users/10086')
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

        resp = self.get_helper(url='/api/v2/auth/users/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp).get('username'), 'ada')

        self.signin_as_admin()

        resp = self.get_helper(url='/api/v2/auth/users/1')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp).get('username'), 'ada')

        resp = self.get_helper(url='/api/v2/auth/users/10086')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_signout(self):
        self.signin_helper()

        resp = self.delete_helper(url='/api/v2/auth/signin')
        self.assertEqual(resp.status_code, HTTPStatus.OK, resp.json)

        resp = self.get_helper(url='/api/v2/auth/users/1')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

    @patch('fedlearner_webconsole.auth.apis.SsoHandlerFactory.get_handler')
    @patch('fedlearner_webconsole.auth.third_party_sso.requests.post')
    @patch('fedlearner_webconsole.auth.third_party_sso.requests.get')
    def test_signin_oauth(self, mock_request_get, mock_request_post, mock_sso_handler):

        mock_sso_handler.return_value = OAuthHandler(Sso(name='test', oauth=OAuthProtocol()))
        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        mock_request_post.return_value = FakeResponse({}, HTTPStatus.OK)
        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={'code': 'wrong_code'})
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

        mock_request_post.return_value = FakeResponse({'access_token': 'token'}, HTTPStatus.OK)
        self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={'code': 'right_code'})
        mock_request_get.assert_called_once()
        get_user_info_with_cache.cache_clear()
        mock_request_get.return_value = FakeResponse({'username': 'test', 'email': 'test'}, HTTPStatus.OK)
        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={'code': 'right_code'})
        data = self.get_response_data(resp)
        self.assertEqual(data['user']['username'], 'test')
        # test oauth sign in after deleted
        with db.session_scope() as session:
            user = UserService(session).get_user_by_username(data['user']['username'])
            user.state = State.DELETED
            session.commit()
        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={'code': 'right_code'})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

    @patch('fedlearner_webconsole.auth.apis.SsoHandlerFactory.get_handler')
    @patch('fedlearner_webconsole.auth.third_party_sso.requests.get')
    def test_signin_cas(self, mock_request_get, mock_sso_handler):
        mock_sso_handler.return_value = CasHandler(Sso(name='test', cas=CasProtocol()))
        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={'ticket': 'wrong_ticket'})
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        mock_request_get.assert_called_once()
        fake_xml = """
        <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
            <cas:authenticationSuccess>
                <cas:user>test3
                </cas:user>
            </cas:authenticationSuccess>
        </cas:serviceResponse>
        """
        mock_request_get.return_value = FakeResponse(None, HTTPStatus.OK, fake_xml)
        resp = self.post_helper(url='/api/v2/auth/signin?sso_name=test', data={'ticket': 'right_code'})
        data = self.get_response_data(resp)
        self.assertEqual(data['user']['username'], 'test3')


class SsoInfosApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with open(f'{Envs.BASE_DIR}/testing/test_data/test_sso.json', encoding='utf-8') as f:
            sso_infos_dict = json.load(f)
        self.patch_ssoinfos = patch('fedlearner_webconsole.auth.third_party_sso.Envs.SSO_INFOS',
                                    json.dumps(sso_infos_dict))
        self.patch_ssoinfos.start()

    def tearDown(self):
        self.patch_ssoinfos.stop()

    def test_get_sso_infos(self):
        with patch('fedlearner_webconsole.auth.apis.sso_info_manager', SsoInfos()):
            resp = self.get_helper(url='/api/v2/auth/sso_infos')
            data = self.get_response_data(resp)
            self.assertEqual(len(data), 2)
            self.assertTrue(data[0].get('oauth'))
            self.assertEqual(data[0]['oauth'].get('secret'), '')


class SelfUserApiTest(BaseTestCase):

    def test_get_self_user(self):
        resp = self.get_helper(url='/api/v2/auth/self')
        self.assertEqual(self.get_response_data(resp)['name'], 'ada')
        self.signout_helper()
        resp = self.get_helper(url='/api/v2/auth/self')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual('failed to find x-pc-auth or authorization within headers', resp.json.get('message'))


class StrictSignInServiceTest(BaseTestCase):

    def test_sign_in(self):
        self.post_helper(f'{API_VERSION}/auth/signin', data={'username': 'ada', 'password': base64encode('fl@.')})
        self.post_helper(f'{API_VERSION}/auth/signin', data={'username': 'ada', 'password': base64encode('fl@.')})
        resp = self.post_helper(f'{API_VERSION}/auth/signin',
                                data={
                                    'username': 'ada',
                                    'password': base64encode('fl@.')
                                })
        self.assertStatus(resp, HTTPStatus.BAD_REQUEST)
        resp = self.post_helper(f'{API_VERSION}/auth/signin',
                                data={
                                    'username': 'ada',
                                    'password': base64encode('fl@12345.')
                                })
        self.assertStatus(resp, HTTPStatus.FORBIDDEN)
        self.assertEqual('Account is locked', resp.json['message'])

    def test_banned_time(self):
        self.post_helper(f'{API_VERSION}/auth/signin', data={'username': 'ada', 'password': base64encode('fl@.')})
        self.post_helper(f'{API_VERSION}/auth/signin', data={'username': 'ada', 'password': base64encode('fl@.')})
        self.post_helper(f'{API_VERSION}/auth/signin', data={'username': 'ada', 'password': base64encode('fl@.')})
        resp = self.post_helper(f'{API_VERSION}/auth/signin',
                                data={
                                    'username': 'ada',
                                    'password': base64encode('fl@12345.')
                                })
        self.assertStatus(resp, HTTPStatus.FORBIDDEN)
        with db.session_scope() as session:
            session.query(User).filter(User.username == 'ada').first().last_sign_in_at = now() - timedelta(minutes=31)
            session.commit()
        resp = self.post_helper(f'{API_VERSION}/auth/signin',
                                data={
                                    'username': 'ada',
                                    'password': base64encode('fl@12345.')
                                })
        self.assertStatus(resp, HTTPStatus.OK)

    def test_change_password(self):
        with db.session_scope() as session:
            user_id = UserService(session).get_user_by_username('ada').id
            self.assertIsNotNone(session.query(SessionTbl).filter(SessionTbl.user_id == user_id).first())
        self.signin_as_admin()
        self.patch_helper(f'{API_VERSION}/auth/users/{user_id}', data={'password': base64encode('flfl123123.')})
        with db.session_scope() as session:
            self.assertIsNone(session.query(SessionTbl).filter(SessionTbl.user_id == user_id).first())


if __name__ == '__main__':
    unittest.main()
