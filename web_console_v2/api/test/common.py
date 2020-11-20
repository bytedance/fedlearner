# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import logging
import secrets
from flask_testing import TestCase
from fedlearner_webconsole.app import create_app, db
from fedlearner_webconsole.auth.models import User

class BaseTestCase(TestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = secrets.token_urlsafe(64)
    PROPAGATE_EXCEPTIONS = True
    LOGGING_LEVEL = logging.DEBUG

    def create_app(self):
        return create_app(self)

    def setUp(self):
        db.create_all()
        user = User(username='ada')
        user.set_password('ada')
        db.session.add(user)
        db.session.commit()

        self.signin_helper()
    
    def tearDown(self):
        self.signout_helper()

        db.session.remove()
        db.drop_all()
    
    def signin_helper(self, username='ada', password='ada'):
        resp = self.client.post(
            '/api/v2/auth/signin',
            data=json.dumps({
                'username': username,
                'password': password
            }),
            content_type='application/json')
        self.assertTrue('access_token' in resp.json)
        self.assertTrue(len(resp.json.get('access_token')) > 1)
        self._token = resp.json.get('access_token')
        return self._token
    
    def signout_helper(self):
        self._token = None
    
    def post_helper(self, url, data, use_auth=True):
        headers = {}
        if use_auth and self._token:
            headers['Authorization'] = 'Bearer %s'%self._token

        resp = self.client.post(
            url, data=json.dumps(data),
            content_type='application/json',
            headers=headers)
        
        return resp

