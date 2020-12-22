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

from testing.common import BaseTestCase

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

if ROLE == 'leader':
    Config = LeaderConfig
else:
    Config = FollowerConfig

class WorkflowTest(Config, BaseTestCase):
    def test_workflow(self):
        if ROLE == 'leader':
            self.leader_test_workflow()
        else:
            self.follower_test_workflow()
    
    def leader_test_workflow(self):
        pass
    
    def follower_test_workflow(self):
        pass



if __name__ == '__main__':
    unittest.main()
