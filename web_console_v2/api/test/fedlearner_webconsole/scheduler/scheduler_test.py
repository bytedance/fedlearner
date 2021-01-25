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
import json
import unittest
import secrets
import logging
import multiprocessing
from http import HTTPStatus

from testing.common import BaseTestCase
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.workflow.models import Workflow

ROLE = os.environ.get('TEST_ROLE', 'leader')

class LeaderConfig(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = secrets.token_urlsafe(64)
    PROPAGATE_EXCEPTIONS = True
    LOGGING_LEVEL = logging.DEBUG
    GRPC_LISTEN_PORT = 1990


class FollowerConfig(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = secrets.token_urlsafe(64)
    PROPAGATE_EXCEPTIONS = True
    LOGGING_LEVEL = logging.DEBUG
    GRPC_LISTEN_PORT = 2990


class WorkflowTest(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL'] = '1'

    @classmethod
    def tearDownClass(cls):
        del os.environ['FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL']

    def get_config(self):
        if ROLE == 'leader':
            return LeaderConfig
        else:
            return FollowerConfig

    def test_workflow(self):
        self._wf_template = {
            'group_alias': 'test-template',
            'job_definitions': [
                {
                    'name': 'job1',
                    'variables': [
                        {
                            'name': 'x',
                            'value': '1',
                            'access_mode': 3
                        }
                    ]
                },
                {
                    'name': 'job2',
                    'variables': [
                        {
                            'name': 'y',
                            'value': '2',
                            'access_mode': 2
                        }
                    ]
                }
            ]
        }
        if ROLE == 'leader':
            self.leader_test_workflow()
        else:
            self.follower_test_workflow()
    
    def setup_project(self, role):
        if role == 'leader':
            peer_role = 'follower'
            peer_port = FollowerConfig.GRPC_LISTEN_PORT
        else:
            peer_role = 'leader'
            peer_port = LeaderConfig.GRPC_LISTEN_PORT

        name = 'test-project'
        config = {
            'domain_name': f'fl-{role}.com',
            'participants': [
                {
                    'name': f'party_{peer_role}',
                    'url': f'127.0.0.1:{peer_port}',
                    'domain_name': f'fl-{peer_role}.com',
                    'grpc_spec': {
                        'egress_url': f'127.0.0.1:{peer_port}',
                    }
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
    
    def leader_test_workflow(self):
        self.setup_project('leader')

        cwf_resp = self.post_helper(
            '/api/v2/workflows',
            data={
                'name': 'test-workflow',
                'project_id': 1,
                'forkable': True,
                'config': self._wf_template,
            })
        self.assertEqual(cwf_resp.status_code, HTTPStatus.CREATED)

        self._check_workflow_state(1, 'READY', 'INVALID', 'READY')

        # test fork
        cwf_resp = self.post_helper(
            '/api/v2/workflows',
            data={
                'name': 'test-workflow2',
                'project_id': 1,
                'forkable': True,
                'forked_from': 1,
                'reuse_job_names': ['job1'],
                'peer_reuse_job_names': ['job2'],
                'config': self._wf_template,
                'fork_proposal_config': {
                    'job_definitions': [
                        {
                            'variables': [
                                {
                                    'name': 'x', 'value': '2'
                                }
                            ]
                        },
                        {
                            'variables': [
                                {
                                    'name': 'y', 'value': '3'
                                }
                            ]
                        }
                    ]
                }
            })
        # import pdb;pdb.set_trace()
        self.assertEqual(cwf_resp.status_code, HTTPStatus.CREATED)
        self._check_workflow_state(2, 'READY', 'INVALID', 'READY')


    def follower_test_workflow(self):
        self.setup_project('follower')
        self._check_workflow_state(1, 'NEW', 'READY', 'PARTICIPANT_PREPARE')

        self.put_helper(
            '/api/v2/workflows/1',
            data={
                'forkable': True,
                'config': self._wf_template,
            })
        self._check_workflow_state(1, 'READY', 'INVALID', 'READY')
        self.assertEqual(len(Job.query.all()), 2)

        # test fork
        json = self._check_workflow_state(2, 'READY', 'INVALID', 'READY')
        self.assertEqual(len(Job.query.all()), 3)
        self.assertEqual(json['data']['reuse_job_names'], ['job2'])
        self.assertEqual(json['data']['peer_reuse_job_names'], ['job1'])
        jobs = json['data']['config']['job_definitions']
        self.assertEqual(jobs[0]['variables'][0]['value'], '2')
        self.assertEqual(jobs[1]['variables'][0]['value'], '2')


    def _check_workflow_state(self, workflow_id, state, target_state,
                              transaction_state):
        while True:
            time.sleep(1)
            resp = self.get_helper('/api/v2/workflows/%d'%workflow_id)
            if resp.status_code != HTTPStatus.OK:
                continue
            if resp.json['data']['state'] == state and \
                    resp.json['data']['target_state'] == target_state and \
                    resp.json['data']['transaction_state'] == transaction_state:
                return resp.json
 
 
def test_main(role):
    global ROLE
    ROLE = role
    unittest.main()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    if ROLE == 'leader':
        process = multiprocessing.Process(target=test_main, args=('follower',))
        process.start()
    test_main(ROLE)
    if ROLE == 'leader':
        assert process.join()
