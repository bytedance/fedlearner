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
import unittest
from http import HTTPStatus

from fedlearner_webconsole.app import create_app, db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import project_pb2, common_pb2
from fedlearner_webconsole.rpc.client import RPCClient
from common import BaseTestCase

class TestRPC(BaseTestCase):
    def test_check_connection(self):
        fed = Project(name='test_fed')
        fed.set_config(
            project_pb2.Project(
                project_name='test_fed',
                self_name='test_party',
                participants={
                    'test_party': project_pb2.Participant(
                        name='test_party',
                        url='localhost:1990',
                        sender_auth_token='test_token',
                        receiver_auth_token='test_token')
                }))
        db.session.add(fed)
        db.session.commit()

        client = RPCClient('test_fed', 'test_party')
        resp = client.check_connection()
        print(resp)
        self.assertEqual(resp.code, common_pb2.STATUS_SUCCESS)

if __name__ == '__main__':
    unittest.main()
