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

import unittest
from http import HTTPStatus

from fedlearner_webconsole.utils.base64 import base64encode
from testing.common import BaseTestCase
from fedlearner_webconsole.auth.models import State, User
from fedlearner_webconsole.db import db_handler as db


class AuthApiTest(BaseTestCase):
    def test_get_all_users(self):
        deleted_user = User(username='deleted_one',
                            email='who.knows@hhh.com',
                            state=State.DELETED)
        with db.session_scope() as session:
            session.add(deleted_user)
            session.commit()

        resp = self.get_helper('/api/v2/auth/users')
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)

        self.signin_as_admin()

        resp = self.get_helper('/api/v2/auth/users')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(len(self.get_response_data(resp)), 2)

    def test_partial_update_user_info(self):
        self.signin_as_admin()
        resp = self.get_helper('/api/v2/auth/users')
        resp_data = self.get_response_data(resp)
        user_id = resp_data[0]['id']
        admin_id = resp_data[1]['id']

        self.signin_helper()
        resp = self.patch_helper('/api/v2/auth/users/10', data={})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

        resp = self.patch_helper(f'/api/v2/auth/users/{user_id}',
                                 data={
                                     'email': 'a_new_email@bytedance.com',
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            self.get_response_data(resp).get('email'),
            'a_new_email@bytedance.com')

        resp = self.patch_helper(f'/api/v2/auth/users/{admin_id}',
                                 data={
                                     'name': 'cannot_modify',
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

        # now we are signing in as admin
        self.signin_as_admin()
        resp = self.patch_helper(f'/api/v2/auth/users/{user_id}',
                                 data={
                                     'role': 'ADMIN',
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(resp).get('role'), 'ADMIN')

        resp = self.patch_helper(f'/api/v2/auth/users/{user_id}',
                                 data={
                                     'password': base64encode('fl@1234.'),
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.OK)

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
        illegal_cases = ['aaaaaaaa', '11111111', '!@#$%^[]',
                         'aaaA1111', 'AAAa!@#$', '1111!@#-',
                         'aa11!@', 'fl@123.',
                         'fl@1234567890abcdefg.']
        legal_case = 'fl@1234.'

        for case in illegal_cases:
            new_user['password'] = base64encode(case)
            resp = self.post_helper(f'/api/v2/auth/users', data=new_user)
            self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        new_user['password'] = base64encode(legal_case)
        resp = self.post_helper(f'/api/v2/auth/users', data=new_user)
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            self.get_response_data(resp).get('username'), 'fedlearner')

        # test_repeat_create
        resp = self.post_helper(f'/api/v2/auth/users', data=new_user)
        self.assertEqual(resp.status_code, HTTPStatus.CONFLICT)

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


if __name__ == '__main__':
    unittest.main()
