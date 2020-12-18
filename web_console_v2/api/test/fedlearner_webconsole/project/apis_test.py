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
import unittest

from base64 import b64encode
from http import HTTPStatus
from google.protobuf.json_format import ParseDict
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto.project_pb2 import Project as ProjectProto, Certificate


class ProjectApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'test.tar.gz'), 'rb') as file:
            self.TEST_CERTIFICATES = str(b64encode(file.read()), encoding='utf-8')
        self.default_project = Project()
        self.default_project.name = 'test-self.default_project'
        self.default_project.set_config(ParseDict({
            'participants': {
                'fl-test.com': {
                    'name': 'test-participant',
                    'domain_name': 'fl-test.com',
                    'grpcSpec': {
                        'url': 'https://127.0.0.1:32443',
                    }
                }
            },
            'variables': [
                {
                    'name': 'test',
                    'value': 'test'
                }
            ]
        }, ProjectProto()))
        self.default_project.set_certificate(ParseDict({
            'certificate': {'*.fl-test.com': self.TEST_CERTIFICATES},
        }, Certificate()))
        self.default_project.comment = 'test comment'
        db.session.add(self.default_project)
        db.session.commit()

    def test_get_project(self):
        get_response = self.client.get(
            '/api/v2/projects/{}'.format(1)
        )
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        queried_project = json.loads(get_response.data).get('data')
        self.assertEqual(queried_project, self.default_project.to_dict())

    def test_get_not_found_project(self):
        get_response = self.client.get(
            '/api/v2/projects/{}'.format(1000)
        )
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_project(self):
        name = 'test-post-project'
        config = {
            'participants': {
                'fl-test-post.com': {
                    'name': 'test-post-participant',
                    'url': 'https://127.0.0.1:32443',
                    'certificates': self.TEST_CERTIFICATES
                }
            },
            'variables': [
                {
                    'name': 'test-post',
                    'value': 'test'
                }
            ]
        }
        comment = 'test post project'
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

        queried_project = Project.query.filter_by(name=name).first()
        self.assertEqual(created_project, queried_project.to_dict())

    def test_post_conflict_name_project(self):
        config = {
            'participants': {
                'fl-test-post.com': {
                    'name': 'test-post-participant',
                    'url': 'https://127.0.0.1:32443',
                    'certificates': self.TEST_CERTIFICATES
                }
            },
            'variables': [
                {
                    'name': 'test-post',
                    'value': 'test'
                }
            ]
        }
        create_response = self.client.post(
            '/api/v2/projects',
            data=json.dumps({
                'name': self.default_project.name,
                'config': config,
                'comment': ''
            }),
            content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.BAD_REQUEST)

    def test_list_project(self):
        list_response = self.client.get('/api/v2/projects')
        project_list = json.loads(list_response.data).get('data')
        for project in project_list:
            queried_project = Project.query.filter_by(name=project['name']).first()
            self.assertEqual(project, queried_project.to_dict())

    def test_update_project(self):
        updated_comment = 'updated comment'
        update_response = self.client.patch(
            '/api/v2/projects/{}'.format(1),
            data=json.dumps({
                'comment': updated_comment
            }),
            content_type='application/json')
        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        queried_project = Project.query.filter_by(id=1).first()
        self.assertEqual(queried_project.comment, updated_comment)

    def test_update_not_found_project(self):
        updated_comment = 'updated comment'
        update_response = self.client.patch(
            '/api/v2/projects/{}'.format(1000),
            data=json.dumps({
                'comment': updated_comment
            }),
            content_type='application/json')
        self.assertEqual(update_response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == '__main__':
    unittest.main()
