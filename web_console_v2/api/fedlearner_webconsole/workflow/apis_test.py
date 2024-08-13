# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import random
import string
import time
import json
import unittest
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from unittest.mock import (patch, call)
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.utils.const import SYSTEM_WORKFLOW_CREATOR_USERNAME
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import ItemStatus
from fedlearner_webconsole.dataset.models import Dataset, DatasetType
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.proto.composer_pb2 import WorkflowCronJobInput, RunnerInput
from fedlearner_webconsole.proto.workflow_definition_pb2 import \
    WorkflowDefinition
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.scheduler.transaction import TransactionState
from fedlearner_webconsole.proto import (project_pb2, service_pb2, common_pb2)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from testing.common import BaseTestCase


class WorkflowsApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        self.maxDiff = None
        super().setUp()
        # Inserts data
        template1 = WorkflowTemplate(name='t1', comment='comment for t1', group_alias='g1')
        template1.set_config(WorkflowDefinition(group_alias='g1',))
        workflow1 = Workflow(name='workflow_key_get1',
                             project_id=1,
                             state=WorkflowState.READY,
                             target_state=WorkflowState.INVALID,
                             transaction_state=TransactionState.READY,
                             creator=SYSTEM_WORKFLOW_CREATOR_USERNAME,
                             favour=True)
        workflow2 = Workflow(name='workflow_key_get2',
                             project_id=2,
                             state=WorkflowState.NEW,
                             target_state=WorkflowState.READY,
                             transaction_state=TransactionState.COORDINATOR_COMMITTABLE)
        workflow3 = Workflow(name='workflow_key_get3', project_id=2)
        workflow4 = Workflow(name='workflow_key_get4',
                             project_id=4,
                             state=WorkflowState.INVALID,
                             target_state=WorkflowState.INVALID,
                             transaction_state=TransactionState.READY,
                             favour=True)
        project = Project(id=123, name='project_123')
        dataset1 = Dataset(
            name='default dataset1',
            dataset_type=DatasetType.STREAMING,
            comment='test comment1',
            path='/data/dataset/123',
            project_id=1,
        )
        with db.session_scope() as session:
            session.add(project)
            session.add(workflow1)
            session.add(workflow2)
            session.add(workflow3)
            session.add(workflow4)
            session.add(template1)
            session.add(dataset1)
            session.commit()

    def test_get_with_name(self):
        response = self.get_helper('/api/v2/projects/0/workflows?name=workflow_key_get3')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'workflow_key_get3')

    def test_get_with_project(self):
        response = self.get_helper('/api/v2/projects/1/workflows')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'workflow_key_get1')

    def test_get_with_keyword(self):
        response = self.get_helper('/api/v2/projects/0/workflows?keyword=key')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]['name'], 'workflow_key_get4')

    def test_get_with_states(self):
        response = self.get_helper('/api/v2/projects/0/workflows?states=configuring&states=ready')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'workflow_key_get2')

    def test_get_with_state_invalid(self):
        response = self.get_helper('/api/v2/projects/0/workflows?states=invalid')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual('workflow_key_get4', data[0]['name'])

    def test_get_with_favour(self):
        response = self.get_helper('/api/v2/projects/0/workflows?favour=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)
        self.assertEqual('workflow_key_get4', data[0]['name'])

    def test_get_with_filter(self):
        filter_exp = urllib.parse.quote('(system=true)')
        response = self.get_helper(f'/api/v2/projects/0/workflows?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual('workflow_key_get1', data[0]['name'])
        filter_exp = urllib.parse.quote('(system=false)')
        response = self.get_helper(f'/api/v2/projects/0/workflows?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 3)

    def test_get_workflows(self):
        # Sleeps 1 second for making workflow create_at bigger
        time.sleep(1)
        workflow = Workflow(name='last', project_id=1)
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()
        response = self.get_helper('/api/v2/projects/0/workflows')
        data = self.get_response_data(response)
        self.assertEqual(data[0]['name'], 'last')

    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    @patch('fedlearner_webconsole.workflow.service.resource_uuid')
    def test_create_new_workflow(self, mock_resource_uuid, mock_wakeup):
        mock_resource_uuid.return_value = 'test-uuid'
        with open(Path(__file__, '../../../testing/test_data/workflow_config.json').resolve(),
                  encoding='utf-8') as workflow_config:
            config = json.load(workflow_config)
        # TODO(hangweiqiang): remove this in workflow test
        extra = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        # extra should be a valid json string so we mock one
        extra = f'{{"parent_job_name":"{extra}"}}'

        local_extra = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        # local_extra should be a valid json string so we mock one
        local_extra = f'{{"model_desc":"{local_extra}"}}'

        workflow = {
            'name': 'test-workflow',
            'project_id': 1234567,
            'forkable': True,
            'comment': 'test-comment',
            'config': config,
            'extra': extra,
            'local_extra': local_extra,
            'template_id': 1,
            'template_revision_id': 1
        }
        response = self.post_helper('/api/v2/projects/1234567/workflows', data=workflow)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        created_workflow = self.get_response_data(response)
        # Check scheduler
        mock_wakeup.assert_called_once_with(created_workflow['id'])
        self.assertIsNotNone(created_workflow['id'])
        self.assertIsNotNone(created_workflow['created_at'])
        self.assertIsNotNone(created_workflow['updated_at'])
        self.assertResponseDataEqual(response, {
            'cron_config': '',
            'name': 'test-workflow',
            'project_id': 1234567,
            'forkable': True,
            'forked_from': 0,
            'is_local': False,
            'metric_is_public': False,
            'comment': 'test-comment',
            'state': 'PARTICIPANT_CONFIGURING',
            'create_job_flags': [1, 1, 1],
            'peer_create_job_flags': [],
            'job_ids': [1, 2, 3],
            'uuid': 'test-uuid',
            'template_revision_id': 1,
            'template_id': 1,
            'creator': 'ada',
            'favour': False,
            'jobs': []
        },
                                     ignore_fields=[
                                         'id', 'created_at', 'updated_at', 'start_at', 'stop_at', 'config',
                                         'editor_info', 'template_info'
                                     ])
        # Check DB
        with db.session_scope() as session:
            self.assertEqual(len(session.query(Workflow).all()), 5)

        # Post again
        mock_wakeup.reset_mock()
        response = self.post_helper('/api/v2/projects/1234567/workflows', data=workflow)
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        # Check mock
        mock_wakeup.assert_not_called()
        # Check DB
        with db.session_scope() as session:
            self.assertEqual(len(session.query(Workflow).all()), 5)

    @patch('fedlearner_webconsole.participant.services.ParticipantService.get_platform_participants_by_project')
    @patch('fedlearner_webconsole.workflow.utils.is_peer_job_inheritance_matched')
    def test_fork_local_workflow(self, mock_is_peer_job_inheritance_matched, mock_get_platform_participants_by_project):
        config = {
            'groupAlias': 'test',
            'job_definitions': [{
                'name': 'raw-data-job',
                'is_federated': False,
                'yaml_template': '{}',
            }]
        }
        config_proto = ParseDict(config, WorkflowDefinition())
        with db.session_scope() as session:
            project = Project(name='test project')
            session.add(project)
            template = WorkflowTemplate(group_alias='test')
            template.set_config(config_proto)
            session.add(template)
            session.flush()
            parent_workflow = Workflow(name='local-workflow',
                                       state=WorkflowState.READY,
                                       forkable=True,
                                       project_id=project.id,
                                       template_id=template.id,
                                       template_revision_id=1)
            parent_workflow.set_config(config_proto)
            session.add(parent_workflow)
            session.commit()

        fork_request = {
            'name': 'test-fork-local-workflow',
            'project_id': project.id,
            'forkable': True,
            'config': config,
            'comment': 'test-comment',
            'forked_from': parent_workflow.id,
            'fork_proposal_config': config,
        }
        response = self.post_helper(f'/api/v2/projects/{project.id}/workflows', data=fork_request)
        mock_get_platform_participants_by_project.assert_not_called()
        mock_is_peer_job_inheritance_matched.assert_not_called()
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertResponseDataEqual(
            response, {
                'name': 'test-fork-local-workflow',
                'project_id': project.id,
                'template_id': template.id,
                'template_revision_id': 1,
                'comment': 'test-comment',
                'metric_is_public': False,
                'create_job_flags': [1],
                'job_ids': [1],
                'forkable': True,
                'forked_from': parent_workflow.id,
                'peer_create_job_flags': [],
                'state': 'PARTICIPANT_CONFIGURING',
                'start_at': 0,
                'stop_at': 0,
                'cron_config': '',
                'is_local': True,
                'creator': 'ada',
                'favour': False,
            },
            ignore_fields=['id', 'uuid', 'created_at', 'updated_at', 'config', 'template_info', 'editor_info', 'jobs'])

    @patch('fedlearner_webconsole.participant.services.ParticipantService.get_platform_participants_by_project')
    @patch('fedlearner_webconsole.workflow.service.is_peer_job_inheritance_matched')
    def test_fork_workflow(self, mock_is_peer_job_inheritance_matched, mock_get_platform_participants_by_project):
        # Prepares data
        with open(Path(__file__, '../../../testing/test_data/workflow_config.json').resolve(),
                  encoding='utf-8') as workflow_config:
            config = json.load(workflow_config)
        with db.session_scope() as session:
            project = Project(id=1, name='test project')
            session.add(project)
            config_proto = ParseDict(config, WorkflowDefinition())
            template = WorkflowTemplate(name='parent-template', group_alias=config['group_alias'])
            template.set_config(config_proto)
            session.add(template)
            session.flush()
            parent_workflow = Workflow(name='parent_workflow',
                                       project_id=1,
                                       template_id=template.id,
                                       state=WorkflowState.READY)
            parent_workflow.set_config(config_proto)
            session.add(parent_workflow)
            session.commit()
        fork_request = {
            'name': 'test-fork-workflow',
            'project_id': project.id,
            'forkable': True,
            'config': config,
            'comment': 'test-comment',
            'forked_from': parent_workflow.id,
            'fork_proposal_config': config,
            'peer_create_job_flags': [1, 1, 1],
        }
        # By default it is not forkable
        response = self.post_helper(f'/api/v2/projects/{project.id}/workflows', data=fork_request)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(json.loads(response.data)['details'], 'workflow not forkable')

        # Forks after parent workflow is forkable
        with db.session_scope() as session:
            parent_workflow = session.query(Workflow).get(parent_workflow.id)
            parent_workflow.forkable = True
            session.commit()
        mock_get_platform_participants_by_project.return_value = None
        mock_is_peer_job_inheritance_matched.return_value = True
        response = self.post_helper(f'/api/v2/projects/{project.id}/workflows', data=fork_request)
        mock_is_peer_job_inheritance_matched.assert_called_once()
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertResponseDataEqual(response, {
            'cron_config': '',
            'name': 'test-fork-workflow',
            'project_id': project.id,
            'forkable': True,
            'forked_from': parent_workflow.id,
            'is_local': False,
            'metric_is_public': False,
            'comment': 'test-comment',
            'state': 'PARTICIPANT_CONFIGURING',
            'create_job_flags': [1, 1, 1],
            'peer_create_job_flags': [1, 1, 1],
            'job_ids': [1, 2, 3],
            'template_id': template.id,
            'template_revision_id': 0,
            'creator': 'ada',
            'favour': False,
        },
                                     ignore_fields=[
                                         'id', 'created_at', 'updated_at', 'start_at', 'stop_at', 'uuid', 'config',
                                         'editor_info', 'template_info', 'jobs'
                                     ])

    @patch('fedlearner_webconsole.composer.composer_service.ComposerService.get_item_status')
    @patch('fedlearner_webconsole.composer.composer_service.ComposerService.collect_v2')
    @patch('fedlearner_webconsole.workflow.apis.scheduler.wakeup')
    def test_post_cron_job(self, mock_wakeup, mock_collect, mock_get_item_status):
        mock_get_item_status.return_value = None
        with open(Path(__file__, '../../../testing/test_data/workflow_config.json').resolve(),
                  encoding='utf-8') as workflow_config:
            config = json.load(workflow_config)
        workflow = {
            'name': 'test-workflow-left',
            'project_id': 123,
            'forkable': True,
            'config': config,
            'cron_config': '*/10 * * * *',
            'template_id': 1
        }
        responce = self.post_helper('/api/v2/projects/123/workflows', data=workflow)
        self.assertEqual(responce.status_code, HTTPStatus.CREATED)

        with open(Path(__file__, '../../../testing/test_data/workflow_config_right.json').resolve(),
                  encoding='utf-8') as workflow_config:
            config = json.load(workflow_config)
        workflow = {
            'name': 'test-workflow-right',
            'project_id': 1234567,
            'forkable': True,
            'config': config,
            'cron_config': '*/10 * * * *',
        }
        responce = self.post_helper('/api/v2/projects/1234567/workflows', data=workflow)
        self.assertEqual(responce.status_code, HTTPStatus.CREATED)

        mock_collect.assert_called()
        mock_wakeup.assert_called()


class WorkflowApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            self._project = Project(id=123, name='project_123')
            self._template1 = WorkflowTemplate(name='t1', comment='comment for t1', group_alias='g1')
            self._template1.set_config(WorkflowDefinition(group_alias='g1',))
            session.add(self._project)
            session.add(self._template1)
            session.commit()
        self.signin_as_admin()

    def test_get_workflow(self):
        workflow = Workflow(name='test-workflow',
                            project_id=self._project.id,
                            config=WorkflowDefinition(group_alias='g1',).SerializeToString(),
                            template_id=self._template1.id,
                            forkable=False,
                            state=WorkflowState.RUNNING,
                            job_ids='1')
        job1 = Job(name='job 1', workflow_id=3, project_id=self._project.id, job_type=JobType.RAW_DATA)
        with db.session_scope() as session:
            session.add(workflow)
            session.add(job1)
            session.commit()

        response = self.get_helper(f'/api/v2/projects/{self._project.id}/workflows/{workflow.id}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        workflow_data = self.get_response_data(response)
        self.assertEqual(workflow_data['name'], 'test-workflow')
        self.assertEqual(len(workflow_data['jobs']), 1)
        self.assertEqual(workflow_data['jobs'][0]['name'], 'job 1')
        response = self.get_helper(f'/api/v2/projects/{self._project.id}/workflows/6666')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('fedlearner_webconsole.scheduler.scheduler.Scheduler.wakeup')
    def test_put_successfully(self, mock_wake_up):
        config = {
            'variables': [{
                'name': 'namespace',
                'value': 'leader'
            }, {
                'name': 'basic_envs',
                'value': '{}'
            }, {
                'name': 'storage_root_dir',
                'value': '/'
            }]
        }
        with db.session_scope() as session:
            project = Project(id=1,
                              name='test',
                              config=ParseDict(config, project_pb2.ProjectConfig()).SerializeToString())
            participant = Participant(name='party_leader', host='127.0.0.1', port=5000, domain_name='fl-leader.com')
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            session.add(project)
            session.add(participant)
            session.add(relationship)
            workflow = Workflow(name='test-workflow',
                                project_id=project.id,
                                state=WorkflowState.NEW,
                                transaction_state=TransactionState.PARTICIPANT_PREPARE,
                                target_state=WorkflowState.READY)
            session.add(workflow)
            session.commit()

        response = self.put_helper(f'/api/v2/projects/{project.id}/workflows/{workflow.id}',
                                   data={
                                       'forkable': True,
                                       'config': {
                                           'group_alias': 'test-template'
                                       },
                                       'comment': 'test comment',
                                       'template_id': 1,
                                       'template_revision_id': 1
                                   })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_wake_up.assert_called_with(workflow.id)
        with db.session_scope() as session:
            updated_workflow = session.query(Workflow).get(workflow.id)
            self.assertIsNotNone(updated_workflow.config)
            self.assertTrue(updated_workflow.forkable)
            self.assertEqual(updated_workflow.comment, 'test comment')
            self.assertEqual(updated_workflow.target_state, WorkflowState.READY)
            self.assertEqual(updated_workflow.template_revision_id, 1)

    def test_put_resetting(self):
        with db.session_scope() as session:
            project_id = 123
            workflow = Workflow(
                name='test-workflow',
                project_id=project_id,
                config=WorkflowDefinition(group_alias='test-template').SerializeToString(),
                state=WorkflowState.NEW,
            )
            session.add(workflow)
            session.commit()
            session.refresh(workflow)

        response = self.put_helper(f'/api/v2/projects/{project_id}/workflows/{workflow.id}',
                                   data={
                                       'forkable': True,
                                       'config': {
                                           'group_alias': 'test-template'
                                       },
                                       'template_id': 1
                                   })
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    @patch('fedlearner_webconsole.composer.composer_service.ComposerService.get_item_status')
    @patch('fedlearner_webconsole.composer.composer_service.ComposerService.patch_item_attr')
    @patch('fedlearner_webconsole.composer.composer_service.ComposerService.finish')
    @patch('fedlearner_webconsole.composer.composer_service.ComposerService.collect_v2')
    def test_patch_cron_config(self, mock_collect, mock_finish, mock_patch_item, mock_get_item_status):
        mock_get_item_status.side_effect = [None, ItemStatus.ON]
        project_id = 123
        workflow = Workflow(
            name='test-workflow-left',
            project_id=project_id,
            config=WorkflowDefinition().SerializeToString(),
            forkable=False,
            state=WorkflowState.STOPPED,
        )
        cron_config = '*/20 * * * *'
        with db.session_scope() as session:
            session.add(workflow)
            session.commit()
            session.refresh(workflow)

        # test create cronjob
        response = self.patch_helper(f'/api/v2/projects/{project_id}/workflows/{workflow.id}',
                                     data={'cron_config': cron_config})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        mock_collect.assert_called_with(
            name=f'workflow_cron_job_{workflow.id}',
            items=[(ItemType.WORKFLOW_CRON_JOB,
                    RunnerInput(workflow_cron_job_input=WorkflowCronJobInput(workflow_id=workflow.id)))],
            cron_config=cron_config)

        # patch new config for cronjob
        cron_config = '*/30 * * * *'
        response = self.patch_helper(f'/api/v2/projects/{project_id}/workflows/{workflow.id}',
                                     data={'cron_config': cron_config})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_patch_item.assert_called_with(name=f'workflow_cron_job_{workflow.id}',
                                           key='cron_config',
                                           value=cron_config)

        # test stop cronjob
        response = self.patch_helper(f'/api/v2/projects/{project_id}/workflows/{workflow.id}', data={'cron_config': ''})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_finish.assert_called_with(name=f'workflow_cron_job_{workflow.id}')

    def test_patch_not_found(self):
        response = self.patch_helper('/api/v2/projects/123/workflows/1', data={'target_state': 'RUNNING'})
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_patch_create_job_flags(self):
        with db.session_scope() as session:
            workflow, job = add_fake_workflow(session)
            job_id = job.id
        response = self.patch_helper(f'/api/v2/projects/{workflow.project_id}/workflows/{workflow.id}',
                                     data={'create_job_flags': [3]})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            patched_job = session.query(Job).get(job_id)
            self.assertEqual(patched_job.is_disabled, True)
        response = self.patch_helper(f'/api/v2/projects/{workflow.project_id}/workflows/{workflow.id}',
                                     data={'create_job_flags': [1]})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            patched_job = session.query(Job).get(job_id)
            self.assertEqual(patched_job.is_disabled, False)

    def test_patch_favour(self):
        with db.session_scope() as session:
            workflow, job = add_fake_workflow(session)
        response = self.patch_helper(f'/api/v2/projects/{workflow.project_id}/workflows/{workflow.id}',
                                     data={'favour': True})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(data['favour'], True)
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow.id)
            self.assertEqual(workflow.favour, True)

    def test_ptach_template(self):
        with db.session_scope() as session:
            workflow, job = add_fake_workflow(session)
        response = self.patch_helper(f'/api/v2/projects/{workflow.project_id}/workflows/{workflow.id}',
                                     data={
                                         'config': to_dict(workflow.get_config()),
                                         'template_revision_id': 1
                                     })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(data['template_revision_id'], 1)
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow.id)
            self.assertEqual(workflow.template_revision_id, 1)

    def test_is_local(self):
        with db.session_scope() as session:
            workflow, job = add_fake_workflow(session)
            self.assertTrue(workflow.is_local())
            config = workflow.get_config()
            config.job_definitions[0].is_federated = True
            workflow.set_config(config)
            self.assertFalse(workflow.is_local())


class WorkflowInvalidateApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project_1')
            participant1 = Participant(name='party_1', id=1, host='127.0.0.1', port=1997, domain_name='fl-party1.com')

            participant2 = Participant(name='party_2', id=2, host='127.0.0.1', port=1998, domain_name='fl-party2.com')
            relationship1 = ProjectParticipant(project_id=1, participant_id=1)
            relationship2 = ProjectParticipant(project_id=1, participant_id=2)
            ready_workflow = Workflow(name='workflow_invalidate1',
                                      project_id=1,
                                      uuid='11111',
                                      state=WorkflowState.NEW,
                                      target_state=WorkflowState.READY,
                                      transaction_state=TransactionState.READY)
            session.add(project)
            session.add(participant1)
            session.add(participant2)
            session.add(relationship1)
            session.add(relationship2)
            session.add(ready_workflow)
            session.commit()
        self.signin_as_admin()

    @patch('fedlearner_webconsole.rpc.client.RpcClient.invalidate_workflow')
    def test_invalidate_after_created(self, mock_invalidate_workflow):
        mock_invalidate_workflow.return_value = service_pb2.InvalidateWorkflowResponse(
            status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS, msg=''),
            succeeded=True,
        )
        response = self.post_helper('/api/v2/projects/1/workflows/1:invalidate')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        expected = [call('11111'), call('11111')]
        self.assertEqual(mock_invalidate_workflow.call_args_list, expected)
        response = self.get_helper('/api/v2/projects/0/workflows/1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(data['state'], WorkflowState.INVALID.name)


class WorkflowStartAndStopApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=1, name='project_1')
            participant1 = Participant(name='party_1', id=1, host='127.0.0.1', port=1997, domain_name='fl-party1.com')

            participant2 = Participant(name='party_2', id=2, host='127.0.0.1', port=1998, domain_name='fl-party2.com')
            relationship1 = ProjectParticipant(project_id=1, participant_id=1)
            relationship2 = ProjectParticipant(project_id=1, participant_id=2)
            workflow_test_start_fed = Workflow(name='workflow_test_start_fed',
                                               project_id=1,
                                               uuid='11111',
                                               state=WorkflowState.READY,
                                               target_state=WorkflowState.INVALID,
                                               transaction_state=TransactionState.READY)
            workflow_test_stop_fed = Workflow(name='workflow_test_stop_fed',
                                              project_id=1,
                                              uuid='22222',
                                              state=WorkflowState.RUNNING,
                                              target_state=WorkflowState.INVALID,
                                              transaction_state=TransactionState.READY)
            workflow_test_start_local = Workflow(name='workflow_test_start_local',
                                                 project_id=1,
                                                 uuid='33333',
                                                 state=WorkflowState.STOPPED,
                                                 target_state=WorkflowState.INVALID,
                                                 transaction_state=TransactionState.READY)
            workflow_test_stop_local = Workflow(name='workflow_test_stop_local',
                                                project_id=1,
                                                uuid='44444',
                                                state=WorkflowState.RUNNING,
                                                target_state=WorkflowState.INVALID,
                                                transaction_state=TransactionState.READY)
            session.add(project)
            session.add(participant1)
            session.add(participant2)
            session.add(relationship1)
            session.add(relationship2)
            session.add(workflow_test_start_fed)
            session.add(workflow_test_stop_fed)
            session.add(workflow_test_start_local)
            session.add(workflow_test_stop_local)
            session.commit()
        self.signin_as_admin()

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager.run')
    def test_start_workflow_fed(self, mock_run):
        mock_run.return_value = (True, '')
        response = self.post_helper('/api/v2/projects/1/workflows/1:start')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_run.assert_called_once()

    @patch('fedlearner_webconsole.two_pc.transaction_manager.TransactionManager.run')
    def test_stop_workflow_fed(self, mock_run):
        mock_run.return_value = (True, '')
        response = self.post_helper('/api/v2/projects/1/workflows/2:stop')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_run.assert_called_once()

    @patch('fedlearner_webconsole.workflow.models.Workflow.is_local')
    @patch('fedlearner_webconsole.workflow.workflow_job_controller.start_workflow_locally')
    def test_start_workflow_local(self, mock_start_workflow_locally, mock_is_local):
        mock_is_local.return_value = True
        response = self.post_helper('/api/v2/projects/1/workflows/3:start')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_start_workflow_locally.assert_called_once()

    @patch('fedlearner_webconsole.workflow.models.Workflow.is_local')
    @patch('fedlearner_webconsole.workflow.workflow_job_controller.stop_workflow_locally')
    def test_stop_workflow_local(self, mock_stop_workflow_locally, mock_is_local):
        mock_is_local.return_value = True
        response = self.post_helper('/api/v2/projects/1/workflows/4:stop')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_stop_workflow_locally.assert_called_once()
        response = self.post_helper('/api/v2/projects/1/workflows/4:stop')
        self.assertEqual(response.status_code, HTTPStatus.OK)


def add_fake_workflow(session):
    wd = WorkflowDefinition()
    jd = wd.job_definitions.add()
    jd.yaml_template = '{}'
    workflow = Workflow(
        name='test-workflow',
        project_id=123,
        config=wd.SerializeToString(),
        forkable=False,
        state=WorkflowState.READY,
    )
    session.add(workflow)
    session.flush()
    job = Job(name='test_job',
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
