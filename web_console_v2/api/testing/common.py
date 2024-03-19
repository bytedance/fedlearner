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
import logging
import unittest
import secrets
from http import HTTPStatus
import multiprocessing as mp
from typing import Dict, List, Union
from unittest.mock import patch

from flask_testing import TestCase

from envs import Envs
from fedlearner_webconsole.auth.services import UserService
from fedlearner_webconsole.composer.composer import composer
from fedlearner_webconsole.db import db
from fedlearner_webconsole.app import create_app
from fedlearner_webconsole.iam.client import create_iams_for_user
from fedlearner_webconsole.initial_db import initial_db
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.utils.pp_base64 import base64encode
from testing.no_web_server_test_case import NoWebServerTestCase


class BaseTestCase(NoWebServerTestCase, TestCase):

    class Config(NoWebServerTestCase.Config):
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        JWT_SECRET_KEY = secrets.token_urlsafe(64)
        PROPAGATE_EXCEPTIONS = True
        LOGGING_LEVEL = logging.DEBUG
        TESTING = True
        ENV = 'development'
        GRPC_LISTEN_PORT = 1990
        START_K8S_WATCHER = False

    def create_app(self):
        app = create_app(self.__class__.Config)
        return app

    def setUp(self):
        super().setUp()
        initial_db()
        self.signin_helper()
        with db.session_scope() as session:
            users = UserService(session).get_all_users()
            for user in users:
                create_iams_for_user(user)

    def tearDown(self):
        self.signout_helper()
        scheduler.stop()
        composer.stop()
        super().tearDown()

    def get_response_data(self, response) -> dict:
        return json.loads(response.data).get('data')

    def signin_as_admin(self):
        self.signout_helper()
        self.signin_helper(username='admin', password='fl@12345.')

    def signin_helper(self, username='ada', password='fl@12345.'):
        resp = self.client.post('/api/v2/auth/signin',
                                data=json.dumps({
                                    'username': username,
                                    'password': base64encode(password)
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

    def post_helper(self, url, data=None, use_auth=True):
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

    def assertResponseDataEqual(self, response, expected_data: Union[Dict, List], ignore_fields=None):
        """Asserts if the data in response equals to expected_data.

        It's actually a comparison between two dicts, if ignore_fields is
        specified then we ignore those fields in response."""
        actual_data = self.get_response_data(response)
        assert type(actual_data) is type(expected_data), 'different type for responce data and expceted data!'
        self.assertPartiallyEqual(actual_data, expected_data, ignore_fields)

    def setup_project(self, role, peer_port):
        if role == 'leader':
            peer_role = 'follower'
        else:
            peer_role = 'leader'
        patch.object(Envs, 'DEBUG', True).start()
        patch.object(Envs, 'GRPC_SERVER_URL', f'127.0.0.1:{peer_port}').start()
        name = 'test-project'
        with db.session_scope() as session:
            participant = Participant(name=f'party_{peer_role}',
                                      host='127.0.0.1',
                                      port=peer_port,
                                      domain_name=f'fl-{peer_role}.com')
            session.add(participant)
            session.commit()

        create_response = self.post_helper('/api/v2/projects', data={
            'name': name,
            'participant_ids': [1],
        })
        self.assertEqual(create_response.status_code, HTTPStatus.CREATED)
        return json.loads(create_response.data).get('data')


class TestAppProcess(mp.get_context('spawn').Process):

    def __init__(self, test_class, method, config=None, result_queue=None):
        super().__init__()
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
            logging.basicConfig(level=logging.DEBUG, format='SPAWN:%(filename)s %(lineno)s %(levelname)s - %(message)s')
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
                # pylint: disable=protected-access
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
                    logging.error('======================================================================')

                    logging.error(f'TestAppProcess ERROR: {method}')
                    logging.error('----------------------------------------------------------------------')
                    logging.error(err)
                    logging.error('----------------------------------------------------------------------')
            if result.failures:
                for method, fail in result.failures:
                    logging.error('======================================================================')
                    logging.error(f'TestAppProcess FAIL: {method}')
                    logging.error('----------------------------------------------------------------------')
                    logging.error(fail)
                    logging.error('----------------------------------------------------------------------')
            assert result.wasSuccessful()
            self._result_queue.put(True)
        except Exception:
            logging.exception('exception happened')
            self._result_queue.put(False)
            raise


def multi_process_test(test_list):
    result_queue = mp.get_context('spawn').Queue()
    proc_list = [TestAppProcess(t['class'], t['method'], t['config'], result_queue) for t in test_list]

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
