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

from unittest.mock import patch
from testing.common import BaseTestCase

from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.models import Job, JobDependency, JobType, JobState
from fedlearner_webconsole.job.service import JobService


class JobServiceTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        workflow_0 = Workflow(id=0, name='test-workflow-0', project_id=0)
        workflow_1 = Workflow(id=1, name='test-workflow-1', project_id=0)
        db.session.add_all([workflow_0, workflow_1])

        config = workflow_definition_pb2.JobDefinition(
            name='test-job').SerializeToString()
        job_0 = Job(id=0,
                    name='raw_data_0',
                    job_type=JobType.RAW_DATA,
                    state=JobState.STARTED,
                    workflow_id=0,
                    project_id=0,
                    config=config)
        job_1 = Job(id=1,
                    name='raw_data_1',
                    job_type=JobType.RAW_DATA,
                    state=JobState.COMPLETED,
                    workflow_id=0,
                    project_id=0,
                    config=config)
        job_2 = Job(id=2,
                    name='data_join_0',
                    job_type=JobType.DATA_JOIN,
                    state=JobState.WAITING,
                    workflow_id=0,
                    project_id=0,
                    config=config)
        job_3 = Job(id=3,
                    name='data_join_1',
                    job_type=JobType.DATA_JOIN,
                    state=JobState.COMPLETED,
                    workflow_id=1,
                    project_id=0,
                    config=config)
        job_4 = Job(id=4,
                    name='train_job_0',
                    job_type=JobType.NN_MODEL_TRANINING,
                    state=JobState.WAITING,
                    workflow_id=1,
                    project_id=0,
                    config=config)
        db.session.add_all([job_0, job_1, job_2, job_3, job_4])

        job_dep_0 = JobDependency(src_job_id=job_0.id,
                                  dst_job_id=job_2.id,
                                  dep_index=0)
        job_dep_1 = JobDependency(src_job_id=job_1.id,
                                  dst_job_id=job_2.id,
                                  dep_index=1)
        job_dep_2 = JobDependency(src_job_id=job_3.id,
                                  dst_job_id=job_4.id,
                                  dep_index=0)

        db.session.add_all([job_dep_0, job_dep_1, job_dep_2])
        db.session.commit()

    def test_is_ready(self):
        job_0 = db.session.query(Job).get(0)
        job_2 = db.session.query(Job).get(2)
        job_4 = db.session.query(Job).get(4)
        job_service = JobService(db.session)
        self.assertTrue(job_service.is_ready(job_0))
        self.assertFalse(job_service.is_ready(job_2))
        self.assertTrue(job_service.is_ready(job_4))

    @patch('fedlearner_webconsole.job.models.Job.is_flapp_failed')
    @patch('fedlearner_webconsole.job.models.Job.is_flapp_complete')
    def test_update_running_state(self, mock_is_complete, mock_is_failed):
        job_0 = db.session.query(Job).get(0)
        job_2 = db.session.query(Job).get(2)
        mock_is_complete.return_value = True
        job_service = JobService(db.session)
        job_service.update_running_state(job_0.name)
        self.assertEqual(job_0.state, JobState.COMPLETED)
        self.assertTrue(job_service.is_ready(job_2))
        job_0.state = JobState.STARTED
        mock_is_complete.return_value = False
        mock_is_failed = True
        job_service.update_running_state(job_0.name)
        self.assertEqual(job_0.state, JobState.FAILED)


