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
import os
import json
from base64 import b64encode
from http import HTTPStatus
from testing.common import BaseTestCase


class ProjectApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'test.tar.gz'), 'rb') as file:
            self.TEST_CERTIFICATES = str(b64encode(file.read()), encoding='utf-8')

    def test_project(self):
        name = 'test-project'
        config = {
            'participants': {
                'fl-test.com': {
                    'name': 'test-participant',
                    'url': 'https://127.0.0.1:32443',
                    'certificates': self.TEST_CERTIFICATES
                }
            },
            'variables': [
                {
                    'name': 'test',
                    'value': 'test'
                }
            ]
        }
        comment = 'test comment'
        create_response = self.client.post(
            '/api/v2/projects',
            data=json.dumps({
                'name': name,
                'config': config,
                'comment': comment
            }),
            content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_project = json.loads(create_response.data).get('data')
        self.assertIsNotNone(created_project.get('token'))

        list_response = self.client.get(
            '/api/v2/projects'
        )
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        project_list = json.loads(list_response.data).get('data')
        self.assertEqual(len(project_list), 1)

        updated_comment = 'updated {}'.format(comment)
        update_response = self.client.put(
            '/api/v2/projects/{}'.format(created_project.get('id')),
            data=json.dumps({
                'name': name,
                'config': config,
                'comment': updated_comment
            }),
            content_type='application/json')
        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        updated_project = json.loads(update_response.data).get('data')
        self.assertEqual(updated_project.get('id'), created_project.get('id'))
        self.assertEqual(updated_project.get('comment'), updated_comment)
