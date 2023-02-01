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
from http import HTTPStatus

from testing.common import BaseTestCase
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.utils.pp_base64 import base64encode
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.db import db


class IamRequiredTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        new_user = {
            'username': 'test_user',
            'password': base64encode('test_user12312'),
            'email': 'hello@bytedance.com',
            'role': 'USER',
            'name': 'codemonkey',
        }
        self.signin_as_admin()
        resp = self.post_helper('/api/v2/auth/users', data=new_user)
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            no_permission_one = User(id=5, username='no_permission_one')
            no_permission_one.set_password('no_permission_one')
            session.add(no_permission_one)
            session.commit()

    def test_workflow_with_iam(self):
        project_id = 123
        workflow = Workflow(
            name='test-workflow',
            project_id=project_id,
            config=WorkflowDefinition().SerializeToString(),
            forkable=False,
            state=WorkflowState.READY,
        )
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()
        self.signin_helper()
        response = self.patch_helper(f'/api/v2/projects/{project_id}/workflows/{workflow.id}',
                                     data={'target_state': 'RUNNING'})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.signin_as_admin()
        response = self.patch_helper(f'/api/v2/projects/{project_id}/workflows/{workflow.id}',
                                     data={'target_state': 'RUNNING'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # test project create hook
        self.signin_helper()
        data = {
            'name': 'test1',
            'config': {
                'variables': [{
                    'name': 'test-post',
                    'value': 'test'
                }]
            },
            'participant_ids': [2]
        }
        resp = self.post_helper('/api/v2/projects', data=data)
        pro_id = self.get_response_data(resp)['id']
        workflow = Workflow(
            name='test-workflow-2',
            project_id=pro_id,
            config=WorkflowDefinition().SerializeToString(),
            forkable=False,
            state=WorkflowState.READY,
        )
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()
        response = self.patch_helper(f'/api/v2/projects/{pro_id}/workflows/{workflow.id}',
                                     data={'target_state': 'RUNNING'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.signin_helper('test_user', 'test_user12312')
        response = self.patch_helper(f'/api/v2/projects/{pro_id}/workflows/{workflow.id}',
                                     data={'target_state': 'RUNNING'})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


if __name__ == '__main__':
    unittest.main()
