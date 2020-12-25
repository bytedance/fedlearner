# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import json
import unittest
from http import HTTPStatus
from pathlib import Path

from testing.common import BaseTestCase


class WorkflowsApiTest(BaseTestCase):
    START_GRPC_SERVER = False
    START_SCHEDULER = False

    def test_create_new_workflow(self):
        with open(
                Path(__file__, '../../test_data/workflow_config.json').resolve()
        ) as workflow_config:
            config = json.load(workflow_config)
        workflow = {
            'name': 'test-workflow',
            'project_id': 1234567,
            'forkable': True,
            'comment': 'test-comment',
            'config': config
        }
        create_response = self.client.post('/api/v2/workflows',
                                           data=json.dumps(workflow),
                                           content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.CREATED)

    def test_fork_workflow(self):
        pass


if __name__ == '__main__':
    unittest.main()
