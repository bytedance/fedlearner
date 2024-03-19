# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from json import loads
from unittest import main
from unittest.mock import patch

from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project


class InitiateE2eJobsApiTest(BaseTestCase):

    def test_post(self):
        self.signin_as_admin()
        response = self.post_helper(
            '/api/v2/e2e_jobs:initiate', {
                'role': 'some_role',
                'name_prefix': 'test',
                'project_name': '',
                'e2e_image_uri': 'invalid',
                'fedlearner_image_uri': 'invalid',
                'platform_endpoint': 'invalid'
            })
        self.assert400(response)
        error_details = loads(response.data)['details']['json']
        self.assertRegex(error_details['role'][0], 'coordinator, participant')
        self.assertRegex(error_details['name_prefix'][0], 'minimum length 5')
        self.assertRegex(error_details['project_name'][0], 'minimum length 1')
        self.assertRegex(error_details['e2e_image_uri'][0], 'Invalid value.')
        self.assertRegex(error_details['fedlearner_image_uri'][0], 'Invalid value.')
        self.assertRegex(error_details['platform_endpoint'][0], 'Not a valid URL')

        response = self.post_helper(
            '/api/v2/e2e_jobs:initiate', {
                'role': 'coordinator',
                'name_prefix': 'test_me',
                'project_name': 'project',
                'e2e_image_uri': 'fedlearner_e2e:hey',
                'fedlearner_image_uri': 'fedlearner:hey',
                'platform_endpoint': 'hey-hello:80/index.html'
            })
        self.assert400(response)
        error_details = loads(response.data)['details']['json']
        self.assertIsNone(error_details.get('role'))
        self.assertIsNone(error_details.get('name_prefix'))
        self.assertIsNone(error_details.get('project_name'))
        self.assertIsNone(error_details.get('e2e_image_uri'))
        self.assertIsNone(error_details.get('fedlearner_image_uri'))
        self.assertRegex(error_details['platform_endpoint'][0], 'Not a valid URL')

        response = self.post_helper(
            '/api/v2/e2e_jobs:initiate', {
                'role': 'coordinator',
                'name_prefix': 'test_me',
                'project_name': 'project',
                'e2e_image_uri': 'fedlearner_e2e:hey',
                'fedlearner_image_uri': 'fedlearner:hey',
                'platform_endpoint': 'http://hey-hello:80/index.html'
            })
        self.assert400(response)
        error_details = loads(response.data)['details']
        self.assertRegex(error_details, 'failed to find project')

        with db.session_scope() as session:
            session.add(Project(id=1000, name='project'))
            session.commit()

        response = self.post_helper(
            '/api/v2/e2e_jobs:initiate', {
                'role': 'coordinator',
                'name_prefix': 'test_me',
                'project_name': 'project',
                'e2e_image_uri': 'fedlearner_e2e:hey',
                'fedlearner_image_uri': 'fedlearner:hey',
                'platform_endpoint': 'http://hey-hello:80/index.html'
            })
        self.assert400(response)
        error_details = loads(response.data)['details']
        self.assertRegex(error_details, r'job with job_name=[\w-]* exists')

        with patch('fedlearner_webconsole.e2e.apis.initiate_all_tests') as mock_initiate_all_tests:
            mock_initiate_all_tests.return_value = [{}]
            response = self.post_helper(
                '/api/v2/e2e_jobs:initiate', {
                    'role': 'coordinator',
                    'name_prefix': 'test_me',
                    'project_name': 'project',
                    'e2e_image_uri': 'fedlearner_e2e:hey',
                    'fedlearner_image_uri': 'fedlearner:hey',
                    'platform_endpoint': 'http://hey-hello:80/index.html'
                })
            self.assert200(response)


if __name__ == '__main__':
    main()
