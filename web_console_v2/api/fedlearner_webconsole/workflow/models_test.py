# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import unittest
from datetime import datetime, timezone

from unittest.mock import patch, PropertyMock

from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowTemplateEditorInfo
from fedlearner_webconsole.proto.workflow_pb2 import WorkflowRef, WorkflowPb
from fedlearner_webconsole.workflow_template.models import WorkflowTemplateRevision, WorkflowTemplate
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import (Workflow, WorkflowState, TransactionState, WorkflowExternalState)
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.project.models import Project
from testing.no_web_server_test_case import NoWebServerTestCase


class WorkflowTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        project = Project(id=0)

        with db.session_scope() as session:
            session.add(project)
            session.commit()

    def test_get_jobs(self):
        workflow = Workflow(id=100, job_ids='1,2,3')
        job1 = Job(id=1, name='job 1', workflow_id=3, project_id=0, job_type=JobType.RAW_DATA)
        job2 = Job(id=2, name='job 2', workflow_id=3, project_id=0, job_type=JobType.RAW_DATA)
        job3 = Job(id=3, name='job 3', workflow_id=100, project_id=0, job_type=JobType.RAW_DATA)
        with db.session_scope() as session:
            session.add_all([workflow, job1, job2, job3])
            session.commit()
            jobs = workflow.get_jobs(session)
        jobs.sort(key=lambda job: job.name)
        self.assertEqual(jobs[0].name, 'job 1')
        self.assertEqual(jobs[1].name, 'job 2')
        self.assertEqual(jobs[2].name, 'job 3')

    def test_workflow_state(self):
        with db.session_scope() as session:
            completed_workflow = Workflow(state=WorkflowState.COMPLETED)
            failed_workflow = Workflow(state=WorkflowState.FAILED)

            stopped_workflow_1 = Workflow(state=WorkflowState.STOPPED, target_state=WorkflowState.INVALID)
            stopped_workflow_2 = Workflow(state=WorkflowState.STOPPED)

            running_workflow = Workflow(state=WorkflowState.RUNNING, target_state=WorkflowState.INVALID)

            warmup_underhood_workflow_1 = Workflow(state=WorkflowState.NEW,
                                                   target_state=WorkflowState.READY,
                                                   transaction_state=TransactionState.PARTICIPANT_COMMITTABLE)
            warmup_underhood_workflow_2 = Workflow(state=WorkflowState.NEW,
                                                   target_state=WorkflowState.READY,
                                                   transaction_state=TransactionState.COORDINATOR_COMMITTING)

            pending_accept_workflow = Workflow(state=WorkflowState.NEW,
                                               target_state=WorkflowState.READY,
                                               transaction_state=TransactionState.PARTICIPANT_PREPARE)

            ready_to_run_workflow = Workflow(state=WorkflowState.READY,
                                             target_state=WorkflowState.INVALID,
                                             transaction_state=TransactionState.READY)

            participant_configuring_workflow_1 = Workflow(state=WorkflowState.NEW,
                                                          target_state=WorkflowState.READY,
                                                          transaction_state=TransactionState.READY)
            participant_configuring_workflow_2 = Workflow(state=WorkflowState.NEW,
                                                          target_state=WorkflowState.READY,
                                                          transaction_state=TransactionState.COORDINATOR_COMMITTABLE)
            participant_configuring_workflow_3 = Workflow(state=WorkflowState.NEW,
                                                          target_state=WorkflowState.READY,
                                                          transaction_state=TransactionState.COORDINATOR_PREPARE)

            invalid_workflow = Workflow(state=WorkflowState.INVALID)

            unknown_workflow = Workflow(state=WorkflowState.NEW, target_state=WorkflowState.INVALID)
            session.add_all([
                completed_workflow, failed_workflow, stopped_workflow_1, stopped_workflow_2, running_workflow,
                warmup_underhood_workflow_1, warmup_underhood_workflow_2, pending_accept_workflow,
                ready_to_run_workflow, participant_configuring_workflow_1, participant_configuring_workflow_2,
                participant_configuring_workflow_3, invalid_workflow, unknown_workflow
            ])
            session.commit()

            completed_job_cw = Job(job_type=JobType.RAW_DATA,
                                   workflow_id=completed_workflow.id,
                                   project_id=0,
                                   state=JobState.COMPLETED)
            failed_job_fw = Job(job_type=JobType.RAW_DATA,
                                workflow_id=failed_workflow.id,
                                project_id=0,
                                state=JobState.FAILED)
            running_job_rw = Job(job_type=JobType.RAW_DATA,
                                 workflow_id=running_workflow.id,
                                 project_id=0,
                                 state=JobState.STARTED)
            session.add_all([completed_job_cw, failed_job_fw, running_job_rw])
            session.commit()

            self.assertEqual(completed_workflow.get_state_for_frontend(), WorkflowExternalState.COMPLETED)
            self.assertEqual(failed_workflow.get_state_for_frontend(), WorkflowExternalState.FAILED)

            self.assertEqual(stopped_workflow_1.get_state_for_frontend(), WorkflowExternalState.STOPPED)
            self.assertEqual(stopped_workflow_2.get_state_for_frontend(), WorkflowExternalState.STOPPED)

            self.assertEqual(running_workflow.get_state_for_frontend(), WorkflowExternalState.RUNNING)

            self.assertEqual(warmup_underhood_workflow_1.get_state_for_frontend(),
                             WorkflowExternalState.WARMUP_UNDERHOOD)
            self.assertEqual(warmup_underhood_workflow_2.get_state_for_frontend(),
                             WorkflowExternalState.WARMUP_UNDERHOOD)

            self.assertEqual(pending_accept_workflow.get_state_for_frontend(), WorkflowExternalState.PENDING_ACCEPT)
            self.assertEqual(ready_to_run_workflow.get_state_for_frontend(), WorkflowExternalState.READY_TO_RUN)

            self.assertEqual(participant_configuring_workflow_1.get_state_for_frontend(),
                             WorkflowExternalState.PARTICIPANT_CONFIGURING)
            self.assertEqual(participant_configuring_workflow_2.get_state_for_frontend(),
                             WorkflowExternalState.PARTICIPANT_CONFIGURING)
            self.assertEqual(participant_configuring_workflow_3.get_state_for_frontend(),
                             WorkflowExternalState.PARTICIPANT_CONFIGURING)

            self.assertEqual(invalid_workflow.get_state_for_frontend(), WorkflowExternalState.INVALID)
            self.assertEqual(unknown_workflow.get_state_for_frontend(), WorkflowExternalState.UNKNOWN)

    def test_to_workflow_ref(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        workflow = Workflow(
            id=123,
            name='test',
            uuid='uuid',
            project_id=1,
            state=WorkflowState.STOPPED,
            target_state=WorkflowState.INVALID,
            created_at=created_at,
            forkable=True,
            metric_is_public=False,
            extra='{}',
        )
        workflow_ref = WorkflowRef(
            id=123,
            name='test',
            uuid='uuid',
            project_id=1,
            state=WorkflowExternalState.STOPPED.name,
            created_at=int(created_at.timestamp()),
            forkable=True,
            metric_is_public=False,
        )
        self.assertEqual(workflow.to_workflow_ref(), workflow_ref)

    def test_to_proto(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        updated_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        workflow = Workflow(id=123,
                            name='test',
                            uuid='uuid',
                            project_id=1,
                            state=WorkflowState.STOPPED,
                            target_state=WorkflowState.INVALID,
                            created_at=created_at,
                            forkable=True,
                            metric_is_public=False,
                            extra='{}',
                            updated_at=updated_at)
        workflow_pb = WorkflowPb(id=123,
                                 name='test',
                                 uuid='uuid',
                                 project_id=1,
                                 state=WorkflowExternalState.STOPPED.name,
                                 created_at=int(created_at.timestamp()),
                                 forkable=True,
                                 metric_is_public=False,
                                 updated_at=int(updated_at.timestamp()),
                                 editor_info=WorkflowTemplateEditorInfo(),
                                 template_info=WorkflowPb.TemplateInfo(is_modified=True))
        self.assertEqual(workflow.to_proto(), workflow_pb)

    @patch('fedlearner_webconsole.workflow.models.Workflow.template_revision', new_callable=PropertyMock)
    @patch('fedlearner_webconsole.workflow.models.Workflow.template', new_callable=PropertyMock)
    def test_get_template_info(self, mock_template, mock_template_revision):
        workflow = Workflow(id=123,
                            name='test',
                            uuid='uuid',
                            project_id=1,
                            template_id=1,
                            template_revision_id=1,
                            config=b'')
        mock_template.return_value = WorkflowTemplate(id=1, name='test', config=b'')
        mock_template_revision.return_value = WorkflowTemplateRevision(id=1, revision_index=3, template_id=1)
        self.assertEqual(workflow.get_template_info(),
                         WorkflowPb.TemplateInfo(name='test', id=1, is_modified=False, revision_index=3))


if __name__ == '__main__':
    unittest.main()
