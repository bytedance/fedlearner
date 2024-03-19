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

from http import HTTPStatus

import flask
import unittest
from unittest.mock import patch

from marshmallow import fields

from fedlearner_webconsole.auth.models import User, Role
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required, input_validator, use_args, use_kwargs
from fedlearner_webconsole.exceptions import InvalidArgumentException, UnauthorizedException
from fedlearner_webconsole.utils.flask_utils import make_flask_response
from testing.common import BaseTestCase


@admin_required
def some_authorized_login():
    return 1


@input_validator
def test_func():
    return 1


class FlaskTest(unittest.TestCase):

    @staticmethod
    def generator_helper(inject_res):
        for r in inject_res:
            yield r

    @patch('fedlearner_webconsole.utils.decorators.pp_flask.get_current_user')
    def test_admin_required(self, mock_get_current_user):
        admin = User(id=0, username='adamin', password='admin', role=Role.ADMIN)
        user = User(id=1, username='ada', password='ada', role=Role.USER)
        mock_get_current_user.return_value = admin
        self.assertTrue(some_authorized_login() == 1)

        mock_get_current_user.return_value = user
        self.assertRaises(UnauthorizedException, some_authorized_login)

    def test_input_validator(self):
        app = flask.Flask(__name__)
        with app.test_request_context('/', json={'name': 'valid_name', 'comment': 'valid comment'}):
            self.assertTrue(test_func() == 1)
        with app.test_request_context('/', json={'name': '', 'comment': 'valid comment'}):
            self.assertRaises(InvalidArgumentException, test_func)
        with app.test_request_context('/', json={'name': '???invalid_name', 'comment': 'valid comment'}):
            self.assertRaises(InvalidArgumentException, test_func)
        with app.test_request_context('/', json={'name': 'a' * 65, 'comment': 'valid comment'}):
            self.assertRaises(InvalidArgumentException, test_func)
        with app.test_request_context('/', json={'name': 'valid_name', 'comment': 'a' * 201}):
            self.assertRaises(InvalidArgumentException, test_func)
        with app.test_request_context('/', json={'name': 'valid_name'}):
            self.assertTrue(test_func() == 1)
        with app.test_request_context('/', json={'unrelated': '??'}):
            self.assertTrue(test_func() == 1)
        with app.test_request_context('/', json={'name': 'valid_name.test'}):
            self.assertTrue(test_func() == 1)


class ParserTest(BaseTestCase):

    def test_unknown_query(self):

        @self.app.route('/hello')
        @use_args({'msg': fields.String(required=True)}, location='query')
        def test_route(params):
            return make_flask_response({'msg': params['msg']})

        resp = self.get_helper('/hello?msg=123&unknown=fff', use_auth=False)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'msg': '123'})

    def test_unknown_body(self):

        @self.app.route('/test_create', methods=['POST'])
        @use_kwargs({'msg': fields.String(required=True)}, location='json')
        def test_route(msg: str):
            return make_flask_response({'msg': msg})

        resp = self.post_helper('/test_create?ufj=4', use_auth=False, data={
            'msg': 'hello',
            'unknown': 'fasdf',
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {'msg': 'hello'})

    def test_invalid_parameter(self):

        @self.app.route('/test', methods=['POST'])
        @use_kwargs({'n': fields.Integer(required=True)}, location='json')
        def test_route(n: int):
            return make_flask_response({'n': n})

        resp = self.post_helper('/test', use_auth=False, data={
            'n': 'hello',
        })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)


if __name__ == '__main__':
    unittest.main()
