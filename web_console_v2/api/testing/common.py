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
import os
import time
import traceback
from fedlearner_webconsole.initial_db import initial_db
import json
import logging
import unittest
import secrets
from http import HTTPStatus
import multiprocessing as mp

from flask import Flask
from flask_testing import TestCase
from fedlearner_webconsole.app import create_app
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import Role, User, State

class BaseTestCase(TestCase):
    class Config(object):
        SQLALCHEMY_DATABASE_URI = 'sqlite://'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        JWT_SECRET_KEY = secrets.token_urlsafe(64)
        PROPAGATE_EXCEPTIONS = True
        LOGGING_LEVEL = logging.DEBUG
        TESTING = True
        ENV = 'development'
        GRPC_LISTEN_PORT = 1990

    def create_app(self):
        app = create_app(self.__class__.Config)
        app.app_context().push()
        return app

    def setUp(self):
        db.create_all()
        initial_db()
        self.signin_helper()

    def tearDown(self):
        self.signout_helper()

        db.session.remove()
        db.drop_all()

    def get_response_data(self, response):
        return json.loads(response.data).get('data')

    def signin_as_admin(self):
        self.signout_helper()
        self.signin_helper(username='admin', password='admin')

    def signin_helper(self, username='ada', password='ada'):
        resp = self.client.post(
            '/api/v2/auth/signin',
            data=json.dumps({
                'username': username,
                'password': password
            }),
            content_type='application/json')
        resp_data = self.get_response_data(resp)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertTrue('access_token' in resp_data)
        self.assertTrue(len(resp_data.get('access_token')) > 1)
        self._token = resp_data.get('access_token')
        return self._token

    def signout_helper(self):
        self._token = None

    def _get_headers(self, use_auth=True):
        headers = {}
        if use_auth and self._token:
            headers['Authorization'] = f'Bearer {self._token}'
        return headers

    def get_helper(self, url, use_auth=True):
        return self.client.get(
            url, headers=self._get_headers(use_auth))

    def post_helper(self, url, data, use_auth=True):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            headers=self._get_headers(use_auth))

    def put_helper(self, url, data, use_auth=True):
        return self.client.put(
            url,
            data=json.dumps(data),
            content_type='application/json',
            headers=self._get_headers(use_auth))

    def patch_helper(self, url, data, use_auth=True):
        return self.client.patch(
            url,
            data=json.dumps(data),
            content_type='application/json',
            headers=self._get_headers(use_auth))

    def delete_helper(self, url, use_auth=True):
        return self.client.delete(url,
                                  headers=self._get_headers(use_auth))

    def setup_project(self, role, peer_port):
        if role == 'leader':
            peer_role = 'follower'
        else:
            peer_role = 'leader'

        name = 'test-project'
        config = {
            'participants': [
                {
                    'name': f'party_{peer_role}',
                    'url': f'127.0.0.1:{peer_port}',
                    'domain_name': f'fl-{peer_role}.com'
                }
            ],
            'variables': [
                {
                    'name': 'EGRESS_URL',
                    'value': f'127.0.0.1:{peer_port}'
                }
            ]
        }
        create_response = self.post_helper(
            '/api/v2/projects',
            data={
                'name': name,
                'config': config,
            })
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        return json.loads(create_response.data).get('data')


class TestAppProcess(mp.get_context('spawn').Process):
    def __init__(self, test_class, method, config=None):
        super(TestAppProcess, self).__init__()
        self._test_class = test_class
        self._method = method
        self._app_config = config
        self._queue = mp.get_context('spawn').Queue()
        self._parent_conn, self._child_conn = mp.Pipe()
        self._exception = None
        self._other_processes_queues = []
    def run(self):
        try:
            for h in logging.getLogger().handlers[:]:
                logging.getLogger().removeHandler(h)
                h.close()
            logging.basicConfig(
                level=logging.DEBUG,
                format="SPAWN:%(filename)s %(lineno)s %(levelname)s - %(message)s")
            if self._app_config:
                self._test_class.Config = self._app_config
            test = self._test_class(self._method)
            result = unittest.TestResult()
            old_tearDown = test.tearDown
            # because that other tests will use your rpc server or shceduler, so you should wait for
            # others after you finish your test
            def new_tearDown(*args, **kwargs):
                # tell others that you has finished
                for other_q in self._other_processes_queues:
                    other_q.put(None)
                # check if the test success, than wait others to  finish
                if not test._outcome.errors:
                    # wait for others
                    for i in range(len(self._other_queue)):
                        self._queue.get()
                old_tearDown(*args, **kwargs)
            test.tearDown = new_tearDown

            suite = unittest.TestSuite([test])
            res = suite.run(result)
            if res.errors:
                for method, err in res.errors:
                    print('======================================================================')
                    print('ERROR:', method)
                    print('----------------------------------------------------------------------')
                    print(err)
                    print('----------------------------------------------------------------------')
            if res.failures:
                for method, fail in res.failures:
                    print('======================================================================')
                    print('FAIL:', method)
                    print('----------------------------------------------------------------------')
                    print(fail)
                    print('----------------------------------------------------------------------')
            assert res.wasSuccessful()
        except Exception as e:
            tb = traceback.format_exc()
            self._child_conn.send((e, tb))

    def join(self):
        ret = super(TestAppProcess, self).join()
        assert self.exitcode == 0, "Subprocess failed!"
        return ret

    @property
    def exception(self):
        if self._parent_conn.poll():
            self._exception = self._parent_conn.recv()
        return self._exception


def multi_process_test(test_list):
    proc_list = [TestAppProcess(t['class'], t['method'], t['config']) for t in test_list]
    for p in proc_list:
        for other_p in proc_list:
            if other_p != p:
                p._other_processes_queues.append(other_p._queue)
        p.start()
    # if one test failed then tell others to stop
    while any([p.is_alive() for p in proc_list]):
        for i, p in enumerate(proc_list):
            if p.exception:
                error, tb = p.exception
                for p_other in proc_list:
                    p_other.terminate()
                print('----------------------------------------------------------------------')
                print('Subprocess failed: number ', i)
                print('----------------------------------------------------------------------')
        time.sleep(2)
    for p in proc_list:
        p.join()

def create_test_db():
    """Creates test db for testing non flask-must units."""
    app = Flask('fedlearner_webconsole_test')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    # this does the binding
    app.app_context().push()
    return db
