# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import logging
import random
import string
import time
import json
import unittest
from uuid import UUID
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.composer.models import ItemStatus, SchedulerItem
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.cronjob import WorkflowCronJobItem
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.scheduler.transaction import TransactionState
from fedlearner_webconsole.proto.service_pb2 import GetWorkflowResponse
from fedlearner_webconsole.proto import project_pb2
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.proto.common_pb2 import CreateJobFlag
from fedlearner_webconsole.workflow.apis import is_peer_job_inheritance_matched
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db_handler

class WorkflowsApiTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        START_GRPC_SERVER = False
        START_SCHEDULER = False

    def setUp(self):
        self.maxDiff = None
        super().setUp()
        # Inserts data
        workflow1 = Workflow(name='workflow_key_get1', project_id=1)
        workflow2 = Workflow(name='workflow_kay_get2', project_id=2)
        workflow3 = Workflow(name='workflow_key_get3', project_id=2)
        db.session.add(workflow1)
        db.session.add(workflow2)
        db.session.add(workflow3)
        db.session.commit()

    def test_get_with_project(self):
        response = self.get_helper('/api/v2/workflows?project=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'workflow_key_get1')

    def test_get_with_keyword(self):
        response = self.get_helper('/api/v2/workflows?keyword=key')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'workflow_key_get1')

    def test_get_workflows(self):
        time.sleep(1)
        workflow = Workflow(name='last', project_id=1)
        db.session.add(workflow)
        db.session.flush()
        db.session.commit()
        response = self.get_helper('/api/v2/workflows')
        data = self.get_response_data(response)
        self.assertEqual(data[0]['name'], 'last')

    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    @patch('fedlearner_webconsole.workflow.apis.uuid4')
    def test_create_new_workflow(self, mock_uuid, mock_wakeup):
        mock_uuid.return_value = UUID('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        with open(
                Path(__file__, '../../test_data/workflow_config.json').resolve(
                )) as workflow_config:
            config = json.load(workflow_config)
        extra = ''.join(
            random.choice(string.ascii_lowercase) for _ in range(10))
        # extra should be a valid json string so we mock one
        extra = f'{{"parent_job_name":"{extra}"}}'
        workflow = {
            'name': 'test-workflow',
            'project_id': 1234567,
            'forkable': True,
            'comment': 'test-comment',
            'config': config,
            'extra': extra
        }
        response = self.post_helper('/api/v2/workflows', data=workflow)
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
        del created_workflow['start_at']
        del created_workflow['stop_at']
        self.assertEqual(
            created_workflow, {
                'batch_update_interval': -1,
                'name': 'test-workflow',
                'project_id': 1234567,
                'extra': extra,
                'forkable': True,
                'forked_from': None,
                'metric_is_public': False,
                'comment': 'test-comment',
                'state': 'NEW',
                'target_state': 'READY',
                'transaction_state': 'READY',
                'transaction_err': None,
                'create_job_flags': [1, 1, 1],
                'peer_create_job_flags': None,
                'job_ids': [],
                'transaction_state': 'READY',
                'last_triggered_batch': None,
                'recur_at': None,
                'recur_type': 'NONE',
                'trigger_dataset': None,
                'uuid': f'u{mock_uuid().hex[:19]}'
            })
        # Check DB
        self.assertEqual(len(Workflow.query.all()), 4)

        # Post again
        mock_wakeup.reset_mock()
        response = self.post_helper('/api/v2/workflows', data=workflow)
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        # Check mock
        mock_wakeup.assert_not_called()
        # Check DB
        self.assertEqual(len(Workflow.query.all()), 4)

    @patch('fedlearner_webconsole.workflow.apis.composer.get_item_status')
    @patch('fedlearner_webconsole.workflow.apis.composer.collect')
    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    def test_post_batch_update_interval_job(self, mock_wakeup, mock_collect,
                                            mock_get_item_status):
        mock_get_item_status.return_value = None
        with open(
                Path(__file__, '../../test_data/workflow_config.json').resolve(
                )) as workflow_config:
            config = json.load(workflow_config)
        workflow = {
            'name': 'test-workflow-left',
            'project_id': 1234567,
            'forkable': True,
            'config': config,
            'batch_update_interval': 10,
        }
        responce = self.post_helper('/api/v2/workflows', data=workflow)
        self.assertEqual(responce.status_code, HTTPStatus.CREATED)

        with open(
                Path(__file__, '../../test_data/workflow_config_right.json').
                resolve()) as workflow_config:
            config = json.load(workflow_config)
        workflow = {
            'name': 'test-workflow-right',
            'project_id': 1234567,
            'forkable': True,
            'config': config,
            'batch_update_interval': 10,
        }
        responce = self.post_helper('/api/v2/workflows', data=workflow)
        self.assertEqual(responce.status_code, HTTPStatus.BAD_REQUEST)

        mock_collect.assert_called()
        mock_wakeup.assert_called()

    def test_fork_workflow(self):
        # TODO: insert into db first, and then copy it.
        pass


class WorkflowApiTest(BaseTestCase):
    def test_put_successfully(self):
        config = {
            'participants': [{
                'name': 'party_leader',
                'url': '127.0.0.1:5000',
                'domain_name': 'fl-leader.com'
            }],
            'variables': [{
                'name': 'namespace',
                'value': 'leader'
            }, {
                'name': 'basic_envs',
                'value': '{}'
            }, {
                'name': 'storage_root_dir',
                'value': '/'
            }, {
                'name': 'EGRESS_URL',
                'value': '127.0.0.1:1991'
            }]
        }
        project = Project(
            name='test',
            config=ParseDict(config,
                             project_pb2.Project()).SerializeToString())
        db.session.add(project)
        workflow = Workflow(
            name='test-workflow',
            project_id=1,
            state=WorkflowState.NEW,
            transaction_state=TransactionState.PARTICIPANT_PREPARE,
            target_state=WorkflowState.READY)
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.put_helper(f'/api/v2/workflows/{workflow.id}',
                                   data={
                                       'forkable': True,
                                       'config': {
                                           'group_alias': 'test-template'
                                       },
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

        response = self.put_helper(f'/api/v2/workflows/{workflow.id}',
                                   data={
                                       'forkable': True,
                                       'config': {
                                           'group_alias': 'test-template'
                                       },
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

        response = self.patch_helper(f'/api/v2/workflows/{workflow.id}',
                                     data={'target_state': 'RUNNING'})
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
        workflow = Workflow(name='test-workflow',
                            project_id=123,
                            config=WorkflowDefinition().SerializeToString(),
                            forkable=False,
                            state=WorkflowState.READY,
                            target_state=WorkflowState.RUNNING)
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.patch_helper(f'/api/v2/workflows/{workflow.id}',
                                     data={'target_state': 'READY'})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            json.loads(response.data).get('details'),
            'Another transaction is in progress [1]')
        # Checks DB
        patched_workflow = Workflow.query.get(workflow.id)
        self.assertEqual(patched_workflow.state, WorkflowState.READY)
        self.assertEqual(patched_workflow.target_state, WorkflowState.RUNNING)
        # Checks scheduler
        mock_wakeup.assert_not_called()

    @patch('fedlearner_webconsole.workflow.apis.composer.get_item_status')
    @patch('fedlearner_webconsole.workflow.apis.composer.patch_item_attr')
    @patch('fedlearner_webconsole.workflow.apis.composer.finish')
    @patch('fedlearner_webconsole.workflow.apis.composer.collect')
    def test_patch_batch_update_interval(self, mock_collect, mock_finish,
                                         mock_patch_item,
                                         mock_get_item_status):
        mock_get_item_status.side_effect = [None, ItemStatus.ON]
        workflow = Workflow(
            name='test-workflow-left',
            project_id=123,
            config=WorkflowDefinition(is_left=True).SerializeToString(),
            forkable=False,
            state=WorkflowState.STOPPED,
        )
        batch_update_interval = 1
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        # test create cronjob
        response = self.patch_helper(
            f'/api/v2/workflows/{workflow.id}',
            data={'batch_update_interval': batch_update_interval})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        mock_collect.assert_called_with(
            name=f'workflow_cron_job_{workflow.id}',
            items=[WorkflowCronJobItem(workflow.id)],
            metadata={},
            interval=batch_update_interval * 60)

        # patch new interval time for cronjob
        batch_update_interval = 2
        response = self.patch_helper(
            f'/api/v2/workflows/{workflow.id}',
            data={'batch_update_interval': batch_update_interval})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_patch_item.assert_called_with(
            name=f'workflow_cron_job_{workflow.id}',
            key='interval_time',
            value=batch_update_interval * 60)

        # test stop cronjob
        response = self.patch_helper(f'/api/v2/workflows/{workflow.id}',
                                     data={'batch_update_interval': -1})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_finish.assert_called_with(name=f'workflow_cron_job_{workflow.id}')

        workflow = Workflow(
            name='test-workflow-right',
            project_id=456,
            config=WorkflowDefinition(is_left=False).SerializeToString(),
            forkable=False,
            state=WorkflowState.STOPPED,
        )
        db.session.add(workflow)
        db.session.commit()
        db.session.refresh(workflow)

        response = self.patch_helper(f'/api/v2/workflows/{workflow.id}',
                                     data={'batch_update_interval': 1})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_patch_not_found(self):
        response = self.patch_helper('/api/v2/workflows/1',
                                     data={'target_state': 'RUNNING'})
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_patch_create_job_flags(self):
        with db_handler.session_scope() as session:
            workflow, job = add_fake_workflow(session)
            response = self.patch_helper(f'/api/v2/workflows/{workflow.id}',
                                         data={'create_job_flags': [3]})
            self.assertEqual(response.status_code, HTTPStatus.OK)
            patched_job = Job.query.get(job.id)
            self.assertEqual(patched_job.is_disabled, True)
            response = self.patch_helper(f'/api/v2/workflows/{workflow.id}',
                                         data={'create_job_flags': [1]})
            self.assertEqual(response.status_code, HTTPStatus.OK)
            patched_job = Job.query.get(job.id)
            self.assertEqual(patched_job.is_disabled, False)

    # TODO: Move it to service_test
    @patch('fedlearner_webconsole.rpc.client.RpcClient.get_workflow')
    def test_is_peer_job_inheritance_matched(self, mock_get_workflow):
        peer_job_0 = JobDefinition(name='raw-data-job')
        peer_job_1 = JobDefinition(name='train-job', is_federated=True)
        peer_config = WorkflowDefinition()
        peer_config.job_definitions.extend([peer_job_0, peer_job_1])
        resp = GetWorkflowResponse(config=peer_config)
        mock_get_workflow.return_value = resp

        job_0 = JobDefinition(name='train-job', is_federated=True)
        config = WorkflowDefinition(job_definitions=[job_0])

        project = Project()
        participant = project_pb2.Participant()
        project.set_config(project_pb2.Project(participants=[participant]))
        workflow0 = Workflow(project=project)
        workflow0.set_config(config)
        db.session.add(workflow0)
        db.session.commit()
        db.session.flush()
        workflow1 = Workflow(project=project, forked_from=workflow0.id)
        workflow1.set_config(config)
        workflow1.set_create_job_flags([CreateJobFlag.REUSE])
        workflow1.set_peer_create_job_flags(
            [CreateJobFlag.NEW, CreateJobFlag.REUSE])

        self.assertTrue(is_peer_job_inheritance_matched(workflow1))

        workflow1.set_create_job_flags([CreateJobFlag.NEW])
        self.assertFalse(is_peer_job_inheritance_matched(workflow1))

    def test_is_local(self):
        with db_handler.session_scope() as session:
            workflow, job = add_fake_workflow(session)
            self.assertTrue(workflow.is_local())
            config = workflow.get_config()
            config.job_definitions[
                0].is_federated = True
            workflow.set_config(config)
            self.assertFalse(False, workflow.is_local())


def add_fake_workflow(session):
    wd = WorkflowDefinition()
    jd = wd.job_definitions.add()
    workflow = Workflow(
        name='test-workflow',
        project_id=123,
        config=wd.SerializeToString(),
        forkable=False,
        state=WorkflowState.READY,
    )
    session.add(workflow)
    session.flush()
    job = Job(
        name='test_job',
        job_type=JobType(1),
        config=jd.SerializeToString(),
        workflow_id=workflow.id,
        project_id=123,
        state=JobState.STOPPED,
        is_disabled=False)
    session.add(job)
    session.flush()
    workflow.job_ids = str(job.id)
    session.commit()
    return workflow, job


if __name__ == '__main__':
    unittest.main()
