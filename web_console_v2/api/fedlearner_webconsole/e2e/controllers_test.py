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

import unittest
from unittest.mock import Mock, patch, call

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.e2e.controllers import initiate_all_tests
from fedlearner_webconsole.proto.e2e_pb2 import E2eJob, InitiateE2eJobsParameter


class E2eControllerTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.e2e.controllers.start_job')
    def test_initiate_participant_tests(self, start_job_mock: Mock):
        start_job_mock.return_value = None
        self.assertRaises(KeyError, initiate_all_tests,
                          InitiateE2eJobsParameter(role='invalid_role', platform_endpoint='some_uri.com'))
        jobs = initiate_all_tests(
            InitiateE2eJobsParameter(role='participant',
                                     name_prefix='test',
                                     project_name='hello',
                                     e2e_image_uri='some_image',
                                     fedlearner_image_uri='some_image',
                                     platform_endpoint='some_uri.com'))
        self.assertEqual([{
            'job_name': 'auto-e2e-test-fed-workflow',
            'job_type': 'fed-workflow'
        }, {
            'job_name': 'auto-e2e-test-vertical-dataset-model-serving',
            'job_type': 'vertical-dataset-model-serving'
        }], jobs)

        self.assertEqual([
            call(
                E2eJob(project_name='hello',
                       script_path='scripts/auto_e2e/fed_workflow/test_participant.py',
                       fedlearner_image_uri='some_image',
                       e2e_image_uri='some_image',
                       job_name='auto-e2e-test-fed-workflow',
                       platform_endpoint='some_uri.com',
                       name_prefix='auto-e2e-test')),
            call(
                E2eJob(project_name='hello',
                       script_path='scripts/auto_e2e/vertical_dataset_model_serving/test_participant.py',
                       fedlearner_image_uri='some_image',
                       e2e_image_uri='some_image',
                       job_name='auto-e2e-test-vertical-dataset-model-serving',
                       platform_endpoint='some_uri.com',
                       name_prefix='auto-e2e-test')),
        ], start_job_mock.call_args_list)

    @patch('fedlearner_webconsole.e2e.controllers.start_job')
    def test_initiate_coordinator_tests(self, start_job_mock: Mock):
        start_job_mock.return_value = None
        jobs = initiate_all_tests(
            InitiateE2eJobsParameter(role='coordinator',
                                     name_prefix='test',
                                     project_name='hello',
                                     e2e_image_uri='some_image',
                                     fedlearner_image_uri='some_image',
                                     platform_endpoint='some_uri.com'))
        self.assertEqual([{
            'job_name': 'auto-e2e-test-fed-workflow',
            'job_type': 'fed-workflow'
        }, {
            'job_name': 'auto-e2e-test-vertical-dataset-model-serving',
            'job_type': 'vertical-dataset-model-serving'
        }], jobs)

        self.assertEqual([
            call(
                E2eJob(project_name='hello',
                       script_path='scripts/auto_e2e/fed_workflow/test_coordinator.py',
                       fedlearner_image_uri='some_image',
                       e2e_image_uri='some_image',
                       job_name='auto-e2e-test-fed-workflow',
                       platform_endpoint='some_uri.com',
                       name_prefix='auto-e2e-test')),
            call(
                E2eJob(project_name='hello',
                       script_path='scripts/auto_e2e/vertical_dataset_model_serving/test_coordinator.py',
                       fedlearner_image_uri='some_image',
                       e2e_image_uri='some_image',
                       job_name='auto-e2e-test-vertical-dataset-model-serving',
                       platform_endpoint='some_uri.com',
                       name_prefix='auto-e2e-test')),
        ], start_job_mock.call_args_list)


if __name__ == '__main__':
    unittest.main()
