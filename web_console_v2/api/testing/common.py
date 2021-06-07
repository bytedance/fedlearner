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
import contextlib
import json
import os
import logging
import unittest
import secrets
from http import HTTPStatus
import multiprocessing as mp

from flask import Flask
from flask_testing import TestCase
from fedlearner_webconsole.composer.composer import Composer, ComposerConfig
from fedlearner_webconsole.db import db
from fedlearner_webconsole.app import create_app
from fedlearner_webconsole.initial_db import initial_db
# NOTE: the following models imported is intended to be analyzed by SQLAlchemy
from fedlearner_webconsole.auth.models import Role, User, State
from fedlearner_webconsole.composer.models import SchedulerItem, SchedulerRunner, OptimisticLock

test_db_path = '/tmp/fedlearner_test.db'


class BaseTestCase(TestCase):
    class Config(object):
        SQLALCHEMY_DATABASE_URI = \
            f'sqlite:///{test_db_path}?check_same_thread=False'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        JWT_SECRET_KEY = secrets.token_urlsafe(64)
        PROPAGATE_EXCEPTIONS = True
        LOGGING_LEVEL = logging.DEBUG
        TESTING = True
        ENV = 'development'
        GRPC_LISTEN_PORT = 1990
        START_COMPOSER = False

    def create_app(self):
        app = create_app(self.__class__.Config)
        app.app_context().push()
        return app

    def setUp(self):
        try:
            # keep clean database before each test
            os.remove(test_db_path)
        except OSError:
            pass

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
        self.signin_helper(username='admin', password='fl@123.')

    def signin_helper(self, username='ada', password='fl@123.'):
        resp = self.client.post('/api/v2/auth/signin',
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
        return self.client.get(url, headers=self._get_headers(use_auth))

    def post_helper(self, url, data, use_auth=True):
        return self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json',
                                headers=self._get_headers(use_auth))

    def put_helper(self, url, data, use_auth=True):
        return self.client.put(url,
                               data=json.dumps(data),
                               content_type='application/json',
                               headers=self._get_headers(use_auth))

    def patch_helper(self, url, data, use_auth=True):
        return self.client.patch(url,
                                 data=json.dumps(data),
                                 content_type='application/json',
                                 headers=self._get_headers(use_auth))

    def delete_helper(self, url, use_auth=True):
        return self.client.delete(url, headers=self._get_headers(use_auth))

    def setup_project(self, role, peer_port):
        if role == 'leader':
            peer_role = 'follower'
        else:
            peer_role = 'leader'

        name = 'test-project'
        config = {
            'participants': [{
                'name': f'party_{peer_role}',
                'url': f'127.0.0.1:{peer_port}',
                'domain_name': f'fl-{peer_role}.com'
            }],
            'variables': [{
                'name': 'EGRESS_URL',
                'value': f'127.0.0.1:{peer_port}'
            }]
        }
        create_response = self.post_helper('/api/v2/projects',
                                           data={
                                               'name': name,
                                               'config': config,
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        return json.loads(create_response.data).get('data')

    @contextlib.contextmanager
    def composer_scope(self, config: ComposerConfig):
        with self.app.app_context():
            composer = Composer(config=config)
            composer.run(db.engine)
            yield composer
            composer.stop()


class TestAppProcess(mp.get_context('spawn').Process):
    def __init__(self, test_class, method, config=None, result_queue=None):
        super(TestAppProcess, self).__init__()
        self._test_class = test_class
        self._method = method
        self._app_config = config
        self.queue = mp.get_context('spawn').Queue()
        self.other_process_queues = []
        self._result_queue = result_queue or mp.get_context('spawn').Queue()

    def run(self):
        try:
            # remove all logging handlers to prevent logger sending test's logs to other place
            for h in logging.getLogger().handlers[:]:
                logging.getLogger().removeHandler(h)
                h.close()
            logging.basicConfig(
                level=logging.DEBUG,
                format=
                'SPAWN:%(filename)s %(lineno)s %(levelname)s - %(message)s')
            if self._app_config:
                self._test_class.Config = self._app_config
            test = self._test_class(self._method)

            old_tear_down = test.tearDown

            # because that other tests will use your rpc server or scheduler, so you should wait for
            # others after you finish the test
            def new_tear_down(*args, **kwargs):
                # tell others that you has finished
                for other_q in self.other_process_queues:
                    other_q.put(None)
                # check if the test success, than wait others to finish
                if not test._outcome.errors:
                    # wait for others
                    for i in range(len(self.other_process_queues)):
                        self.queue.get()
                old_tear_down(*args, **kwargs)

            test.tearDown = new_tear_down

            suite = unittest.TestSuite([test])
            result = unittest.TestResult()
            result = suite.run(result)
            if result.errors:
                for method, err in result.errors:
                    print(
                        '======================================================================'
                    )

                    print('ERROR:', method)
                    print(
                        '----------------------------------------------------------------------'
                    )
                    print(err)
                    print(
                        '----------------------------------------------------------------------'
                    )
            if result.failures:
                for method, fail in result.failures:
                    print(
                        '======================================================================'
                    )
                    print('FAIL:', method)
                    print(
                        '----------------------------------------------------------------------'
                    )
                    print(fail)
                    print(
                        '----------------------------------------------------------------------'
                    )
            assert result.wasSuccessful()
            self._result_queue.put(True)
        except Exception:
            self._result_queue.put(False)
            raise


def multi_process_test(test_list):
    result_queue = mp.get_context('spawn').Queue()
    proc_list = [
        TestAppProcess(t['class'], t['method'], t['config'], result_queue)
        for t in test_list
    ]

    for p in proc_list:
        for other_p in proc_list:
            if other_p != p:
                p.other_process_queues.append(other_p.queue)
        p.start()
    # Waits for all processes get finished or any one gets an exception
    for _ in proc_list:
        succeed = result_queue.get()
        if not succeed:
            # Terminates all processes if any one gets an exception
            # So that logs are more readable
            for p in proc_list:
                p.terminate()
            break
    for i, p in enumerate(proc_list):
        p.join()
        if p.exitcode != 0:
            raise Exception(f'Subprocess failed: number {i}')


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
