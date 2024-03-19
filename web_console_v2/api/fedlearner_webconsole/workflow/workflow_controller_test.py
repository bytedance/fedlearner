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
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import JobType, Job, JobState, JobDependency
from fedlearner_webconsole.notification.template import NotificationTemplateName
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.utils.const import SYSTEM_WORKFLOW_CREATOR_USERNAME
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.workflow.models import WorkflowState, Workflow
from fedlearner_webconsole.workflow.workflow_controller import create_ready_workflow, start_workflow_locally, \
    stop_workflow_locally, \
    invalidate_workflow_locally, _notify_if_finished
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from testing.no_web_server_test_case import NoWebServerTestCase


class CreateReadyWorkflowTest(NoWebServerTestCase):

    def test_create_ready_workflow_with_template(self):
        with db.session_scope() as session:
            workflow_template = WorkflowTemplate(
                id=123,
                name='t123',
                group_alias='test group',
            )
            workflow_template.set_config(
                WorkflowDefinition(
                    group_alias='test group',
                    variables=[
                        Variable(name='var'),
                    ],
                ))
            session.add(workflow_template)
            session.commit()

            # Changes one variable
            config = WorkflowDefinition()
            config.CopyFrom(workflow_template.get_config())
            config.variables[0].value = 'new_value'
            workflow = create_ready_workflow(
                session,
                name='workflow1',
                config=config,
                project_id=2333,
                uuid='uuid',
                template_id=workflow_template.id,
            )
            session.commit()
            workflow_id = workflow.id
        with db.session_scope() as session:
            workflow: Workflow = session.query(Workflow).get(workflow_id)
            self.assertPartiallyEqual(
                to_dict(workflow.to_proto()),
                {
                    'id': workflow_id,
                    'name': 'workflow1',
                    'comment': '',
                    'uuid': 'uuid',
                    'project_id': 2333,
                    'creator': SYSTEM_WORKFLOW_CREATOR_USERNAME,
                    'state': 'READY_TO_RUN',
                    'forkable': False,
                    'forked_from': 0,
                    'template_id': 123,
                    'template_revision_id': 0,
                    'template_info': {
                        'id': 123,
                        'is_modified': False,
                        'name': 't123',
                        'revision_index': 0,
                    },
                    'config': {
                        'group_alias':
                            'test group',
                        'job_definitions': [],
                        'variables': [{
                            'access_mode': 'UNSPECIFIED',
                            'name': 'var',
                            'tag': '',
                            'value': 'new_value',
                            'value_type': 'STRING',
                            'widget_schema': '',
                        }],
                    },
                    'is_local': True,
                    'favour': False,
                    'job_ids': [],
                    'jobs': [],
                    'metric_is_public': False,
                    'create_job_flags': [],
                    'peer_create_job_flags': [],
                    'cron_config': '',
                    'editor_info': {
                        'yaml_editor_infos': {},
                    },
                },
                ignore_fields=['created_at', 'updated_at', 'start_at', 'stop_at'],
            )

    def test_create_ready_workflow_without_template(self):
        with db.session_scope() as session:
            # Changes one variable
            config = WorkflowDefinition(
                group_alias='test group',
                variables=[
                    Variable(name='var', value='cofff'),
                ],
            )
            workflow = create_ready_workflow(
                session,
                name='workflow222',
                config=config,
                project_id=23334,
                uuid='uuid222',
            )
            session.commit()
            workflow_id = workflow.id
        with db.session_scope() as session:
            workflow: Workflow = session.query(Workflow).get(workflow_id)
            self.maxDiff = None
            self.assertPartiallyEqual(
                to_dict(workflow.to_proto()),
                {
                    'id': workflow_id,
                    'name': 'workflow222',
                    'comment': '',
                    'uuid': 'uuid222',
                    'project_id': 23334,
                    'creator': SYSTEM_WORKFLOW_CREATOR_USERNAME,
                    'state': 'READY_TO_RUN',
                    'forkable': False,
                    'forked_from': 0,
                    'template_id': 0,
                    'template_revision_id': 0,
                    'template_info': {
                        'id': 0,
                        'is_modified': True,
                        'name': '',
                        'revision_index': 0,
                    },
                    'config': {
                        'group_alias':
                            'test group',
                        'job_definitions': [],
                        'variables': [{
                            'access_mode': 'UNSPECIFIED',
                            'name': 'var',
                            'tag': '',
                            'value': 'cofff',
                            'value_type': 'STRING',
                            'widget_schema': '',
                        }],
                    },
                    'is_local': True,
                    'favour': False,
                    'job_ids': [],
                    'jobs': [],
                    'metric_is_public': False,
                    'create_job_flags': [],
                    'peer_create_job_flags': [],
                    'cron_config': '',
                    'editor_info': {
                        'yaml_editor_infos': {},
                    },
                },
                ignore_fields=['created_at', 'updated_at', 'start_at', 'stop_at'],
            )


class StartWorkflowLocallyTest(NoWebServerTestCase):

    def test_start_workflow_locally_invalid_template(self):
        running_workflow = Workflow(id=1, state=WorkflowState.RUNNING)
        with db.session_scope() as session:
            start_workflow_locally(session, running_workflow)

    @patch('fedlearner_webconsole.workflow.workflow_controller.WorkflowService.validate_workflow')
    def test_start_workflow_locally_invalid_state(self, mock_validate_workflow: Mock):
        mock_validate_workflow.return_value = False, ('test_job', 'fake error')
        workflow = Workflow(id=1, state=WorkflowState.READY)
        with db.session_scope() as session:
            self.assertRaisesRegex(ValueError, 'Invalid Variable when try to format the job test_job: fake error',
                                   lambda: start_workflow_locally(session, workflow))

    @patch('fedlearner_webconsole.workflow.workflow_controller.pp_datetime.now')
    @patch('fedlearner_webconsole.job.controller.YamlFormatterService.generate_job_run_yaml')
    @patch('fedlearner_webconsole.workflow.workflow_controller.WorkflowService.validate_workflow')
    def test_start_workflow_locally_successfully(self, mock_validate_workflow: Mock, mock_gen_yaml: Mock,
                                                 mock_now: Mock):
        mock_validate_workflow.return_value = True, None
        now_dt = datetime(2021, 9, 1, 10, 20, tzinfo=timezone.utc)
        mock_now.return_value = now_dt

        workflow_id = 123
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.READY)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=1)
            job2 = Job(id=2,
                       name='test job 2',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=1)
            job_def = JobDependency(src_job_id=2, dst_job_id=1, dep_index=0)
            config = JobDefinition(is_federated=False)
            job1.set_config(config)
            job2.set_config(config)
            session.add_all([workflow, job1, job2, job_def])
            session.commit()
            mock_gen_yaml.return_value = {}
            start_workflow_locally(session, workflow)
            session.commit()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertEqual(workflow.start_at, now_dt.timestamp())
            self.assertEqual(workflow.state, WorkflowState.RUNNING)
            job1 = session.query(Job).get(1)
            job2 = session.query(Job).get(2)
            self.assertEqual(job1.state, JobState.WAITING)
            self.assertEqual(job2.state, JobState.STARTED)
            mock_gen_yaml.assert_called_once()


class StopWorkflowLocallyTest(NoWebServerTestCase):

    def test_stop_workflow_locally_invalid_state(self):
        with db.session_scope() as session:
            new_workflow = Workflow(id=1, state=WorkflowState.NEW)
            self.assertRaisesRegex(RuntimeError, 'invalid workflow state WorkflowState.NEW when try to stop',
                                   lambda: stop_workflow_locally(session, new_workflow))

    @patch('fedlearner_webconsole.workflow.workflow_controller.pp_datetime.now')
    @patch('fedlearner_webconsole.workflow.workflow_controller.stop_job')
    def test_stop_workflow_locally_successfully(self, mock_stop_job: Mock, mock_now: Mock):
        now_dt = datetime(2021, 9, 1, 10, 20, tzinfo=timezone.utc)
        mock_now.return_value = now_dt

        workflow_id = 123
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.RUNNING)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=1)
            job2 = Job(id=2,
                       name='test job 2',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=1)
            session.add_all([workflow, job1, job2])
            session.commit()
            stop_workflow_locally(session, workflow)
            session.commit()
        # Stopped 2 jobs
        self.assertEqual(mock_stop_job.call_count, 2)
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertEqual(workflow.stop_at, now_dt.timestamp())
            self.assertEqual(workflow.state, WorkflowState.STOPPED)

    def test_stop_ready_workflow(self):
        with db.session_scope() as session:
            ready_workflow = Workflow(id=1, state=WorkflowState.READY)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=1,
                       project_id=1)
            job2 = Job(id=2,
                       name='test job 2',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=1,
                       project_id=1)
            session.add_all([ready_workflow, job1, job2])
            session.commit()
            stop_workflow_locally(session, ready_workflow)
            self.assertEqual(ready_workflow.state, WorkflowState.STOPPED)

    @patch('fedlearner_webconsole.workflow.workflow_controller.pp_datetime.now')
    @patch('fedlearner_webconsole.workflow.workflow_controller.stop_job')
    def test_stop_workflow_to_completed(self, mock_stop_job: Mock, mock_now: Mock):
        now_dt = datetime(2021, 9, 1, 10, 20, tzinfo=timezone.utc)
        mock_now.return_value = now_dt
        workflow_id = 123
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.RUNNING)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.COMPLETED,
                       workflow_id=workflow_id,
                       project_id=1)
            job2 = Job(id=2,
                       name='test job 2',
                       job_type=JobType.RAW_DATA,
                       state=JobState.COMPLETED,
                       workflow_id=workflow_id,
                       project_id=1)
            session.add_all([workflow, job1, job2])
            session.commit()
            stop_workflow_locally(session, workflow)
            session.commit()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertEqual(workflow.state, WorkflowState.COMPLETED)

    @patch('fedlearner_webconsole.workflow.workflow_controller.stop_job')
    def test_stop_workflow_to_failed(self, mock_stop_job: Mock):
        workflow_id = 123
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.RUNNING)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.COMPLETED,
                       workflow_id=workflow_id,
                       project_id=1)
            job2 = Job(id=2,
                       name='test job 2',
                       job_type=JobType.RAW_DATA,
                       state=JobState.FAILED,
                       workflow_id=workflow_id,
                       project_id=1)
            session.add_all([workflow, job1, job2])
            session.commit()
            stop_workflow_locally(session, workflow)
            session.commit()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertEqual(workflow.state, WorkflowState.FAILED)

    @patch('fedlearner_webconsole.workflow.workflow_controller.stop_job')
    def test_stop_workflow_locally_failed(self, mock_stop_job: Mock):
        mock_stop_job.side_effect = RuntimeError('fake error')

        workflow_id = 123
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, state=WorkflowState.RUNNING)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=1)
            session.add_all([workflow, job1])
            session.commit()
            # Simulates the normal action by following a session commit
            with self.assertRaises(RuntimeError):
                stop_workflow_locally(session, workflow)
                session.commit()
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertIsNone(workflow.stop_at)
            self.assertEqual(workflow.state, WorkflowState.RUNNING)


class InvalidateWorkflowLocallyTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.workflow.workflow_controller.stop_job')
    @patch('fedlearner_webconsole.workflow.workflow_controller.update_cronjob_config')
    def test_invalidate_workflow_locally(self, mock_update_cronjob_config: Mock, mock_stop_job: Mock):
        workflow_id = 6
        project_id = 99
        with db.session_scope() as session:
            workflow = Workflow(id=workflow_id, project_id=project_id, state=WorkflowState.RUNNING)
            job1 = Job(id=1,
                       name='test job 1',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=project_id)
            job2 = Job(id=2,
                       name='test job 2',
                       job_type=JobType.RAW_DATA,
                       state=JobState.NEW,
                       workflow_id=workflow_id,
                       project_id=project_id)
            session.add_all([workflow, job1, job2])
            session.commit()
            invalidate_workflow_locally(session, workflow)
            session.commit()
            mock_update_cronjob_config.assert_called_with(workflow_id, None, session)
        self.assertEqual(mock_stop_job.call_count, 2)
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            self.assertEqual(workflow.state, WorkflowState.INVALID)
            self.assertEqual(workflow.target_state, WorkflowState.INVALID)


@patch('fedlearner_webconsole.workflow.workflow_controller.send_email')
class NotifyIfFinishedTest(NoWebServerTestCase):

    def test_running_workflow(self, mock_send_email: Mock):
        with db.session_scope() as session:
            workflow = Workflow(state=WorkflowState.RUNNING)
            _notify_if_finished(session, workflow)
            mock_send_email.assert_not_called()

    def test_notify(self, mock_send_email: Mock):
        with db.session_scope() as session:
            user = User(username='test_user', email='a@b.com')
            session.add(user)
            session.commit()
        with db.session_scope() as session:
            workflow = Workflow(id=1234, name='test-workflow', state=WorkflowState.FAILED, creator='test_user')
            _notify_if_finished(session, workflow)
            mock_send_email.assert_called_with('a@b.com',
                                               NotificationTemplateName.WORKFLOW_COMPLETE,
                                               name='test-workflow',
                                               state='FAILED',
                                               link='http://localhost:666/v2/workflow-center/workflows/1234')


if __name__ == '__main__':
    unittest.main()
