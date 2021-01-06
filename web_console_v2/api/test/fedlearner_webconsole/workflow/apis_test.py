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
from unittest.mock import patch

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from testing.common import BaseTestCase


class WorkflowsApiTest(BaseTestCase):
    def get_config(self):
        config = super().get_config()
        config.START_GRPC_SERVER = False
        config.START_SCHEDULER = False
        return config

    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    def test_create_new_workflow(self, mock_wakeup):
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
        response = self.client.post('/api/v2/workflows',
                                    data=json.dumps(workflow),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        created_workflow = json.loads(response.data).get('data')
        # Check scheduler
        mock_wakeup.assert_called_once_with(created_workflow['id'])
        self.assertIsNotNone(created_workflow['id'])
        self.assertIsNotNone(created_workflow['created_at'])
        self.assertIsNotNone(created_workflow['updated_at'])
        del created_workflow['id']
        del created_workflow['created_at']
        del created_workflow['updated_at']
        self.assertEqual(created_workflow, {
            'name': 'test-workflow',
            'project_id': 1234567,
            'forkable': True,
            'comment': 'test-comment',
            'config': config,
            'state': 'NEW',
            'target_state': 'READY',
            'transaction_state': 'READY',
            'transaction_err': None,
        })
        # Check DB
        self.assertTrue(len(Workflow.query.all()) == 1)

        # Post again
        mock_wakeup.reset_mock()
        response = self.client.post('/api/v2/workflows',
                                    data=json.dumps(workflow),
                                    content_type='application/json')
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        # Check mock
        mock_wakeup.assert_not_called()
        # Check DB
        self.assertTrue(len(Workflow.query.all()) == 1)

    def test_fork_workflow(self):
        # TODO: insert into db first, and then copy it.
        pass


class WorkflowApiTest(BaseTestCase):
    def test_put_successfully(self):
        workflow = Workflow(
            name='test-workflow',
            project_id=123,
            state=WorkflowState.NEW,
        )
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.put_helper(
            f'/api/v2/workflows/{workflow.id}',
            data={
                'forkable': True,
                'config': {'group_alias': 'test-template'},
                'comment': 'test comment'
            })
        self.assertEqual(response.status_code, HTTPStatus.OK)

        updated_workflow = Workflow.query.get(workflow.id)
        self.assertIsNotNone(updated_workflow.config)
        self.assertTrue(updated_workflow.forkable)
        self.assertEqual(updated_workflow.comment, 'test comment')
        self.assertEqual(updated_workflow.target_state, WorkflowState.READY)

    def test_put_resetting(self):
        workflow = Workflow(
            name='test-workflow',
            project_id=123,
            config=WorkflowDefinition(
                group_alias='test-template').SerializeToString(),
            state=WorkflowState.NEW,
        )
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.put_helper(
            f'/api/v2/workflows/{workflow.id}',
            data={
                'forkable': True,
                'config': {'group_alias': 'test-template'},
            })
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)

    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    def test_patch_successfully(self, mock_wakeup):
        workflow = Workflow(
            name='test-workflow',
            project_id=123,
            config=WorkflowDefinition().SerializeToString(),
            forkable=False,
            state=WorkflowState.READY,
        )
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.patch_helper(
            f'/api/v2/workflows/{workflow.id}',
            data={
                'target_state': 'RUNNING'
            })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        patched_data = json.loads(response.data).get('data')
        self.assertEqual(patched_data['id'], workflow.id)
        self.assertEqual(patched_data['state'], 'READY')
        self.assertEqual(patched_data['target_state'], 'RUNNING')
        # Checks DB
        patched_workflow = Workflow.query.get(workflow.id)
        self.assertEqual(patched_workflow.target_state, WorkflowState.RUNNING)
        # Checks scheduler
        mock_wakeup.assert_called_once_with(workflow.id)

    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    def test_patch_invalid_target_state(self, mock_wakeup):
        workflow = Workflow(
            name='test-workflow',
            project_id=123,
            config=WorkflowDefinition().SerializeToString(),
            forkable=False,
            state=WorkflowState.READY,
            target_state=WorkflowState.RUNNING
        )
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.patch_helper(
            f'/api/v2/workflows/{workflow.id}',
            data={
                'target_state': 'READY'
            })
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(json.loads(response.data).get('details'),
                         'Another transaction is in progress [1]')
        # Checks DB
        patched_workflow = Workflow.query.get(workflow.id)
        self.assertEqual(patched_workflow.state, WorkflowState.READY)
        self.assertEqual(patched_workflow.target_state, WorkflowState.RUNNING)
        # Checks scheduler
        mock_wakeup.assert_not_called()

    def test_patch_not_found(self):
        response = self.patch_helper(
            '/api/v2/workflows/1',
            data={
                'target_state': 'RUNNING'
            })
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == '__main__':
    unittest.main()
