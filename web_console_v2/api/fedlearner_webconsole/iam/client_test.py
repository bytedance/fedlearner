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
from unittest.mock import patch, call

from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.iam.client import check, create_iams_for_resource, create_iams_for_user
from fedlearner_webconsole.iam.permission import Permission
from fedlearner_webconsole.project.models import Project
# must import for db analyze
# pylint: disable=unused-import
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.auth.models import Role


class ClientTest(unittest.TestCase):

    def test_check_invalid_binding(self):
        with self.assertRaises(ValueError) as cm:
            check('xiangyuxuan.prs', '/projects/123/workflows/3', Permission.DATASETS_POST)
        self.assertIn('Invalid binding', str(cm.exception))

    @patch('fedlearner_webconsole.iam.client.checker.check')
    def test_check_false(self, mock_checker):
        mock_checker.return_value = False
        self.assertFalse(check('xprs', '/projects/123/workflows/3', Permission.WORKFLOW_PUT))
        calls = [
            call('xprs', '/', Permission.WORKFLOW_PUT),
            call('xprs', '/projects/123', Permission.WORKFLOW_PUT),
            call('xprs', '/projects/123/workflows/3', Permission.WORKFLOW_PUT),
        ]
        mock_checker.assert_has_calls(calls)

    @patch('fedlearner_webconsole.iam.client.checker.check')
    def test_check_true(self, mock_checker):
        mock_checker.side_effect = [False, True]
        self.assertTrue(check('prs', '/projects/123/workflows/3', Permission.WORKFLOW_PUT))
        calls = [
            call('prs', '/', Permission.WORKFLOW_PUT),
            call('prs', '/projects/123', Permission.WORKFLOW_PUT),
        ]
        mock_checker.assert_has_calls(calls)

    def test_create_iams_for_resource(self):
        username = 'testu'
        project_id = 1111
        self.assertFalse(check(username, f'/projects/{project_id}', Permission.PROJECT_PATCH))
        create_iams_for_resource(Project(id=project_id, name='test'), User(username=username))
        self.assertTrue(check(username, f'/projects/{project_id}', Permission.PROJECT_PATCH))
        workflow_id = 3333
        self.assertTrue(check(username, f'/projects/{project_id}/workflows/{workflow_id}', Permission.WORKFLOW_PATCH))
        self.assertFalse(check(username, f'/projects/{project_id+1}/workflows/{workflow_id}',
                               Permission.WORKFLOW_PATCH))

    def test_create_iams_for_user(self):
        admin = User(username='test_admin', role=Role.ADMIN)
        user = User(username='test_user', role=Role.USER)
        create_iams_for_user(admin)
        create_iams_for_user(user)
        project_id = 1
        self.assertTrue(check(admin.username, f'/projects/{project_id}/workflows/123123', Permission.WORKFLOW_PATCH))
        self.assertFalse(check(user.username, f'/projects/{project_id}/workflows/123123', Permission.WORKFLOW_PATCH))


if __name__ == '__main__':
    unittest.main()
