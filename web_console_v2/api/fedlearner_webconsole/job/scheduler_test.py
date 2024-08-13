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
from unittest.mock import patch, Mock

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.job.scheduler import JobScheduler
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, RunnerOutput, JobSchedulerOutput
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.workflow.models import Workflow  # pylint: disable=unused-import
from testing.no_web_server_test_case import NoWebServerTestCase


class SchedulerTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.job.scheduler.start_job_if_ready')
    def test_run(self, mock_start_job_if_ready: Mock):
        with db.session_scope() as session:
            ready_job = Job(id=1,
                            name='ready_job',
                            job_type=JobType.RAW_DATA,
                            state=JobState.WAITING,
                            workflow_id=1,
                            project_id=1)
            ready_job.set_config(JobDefinition(is_federated=False))
            not_ready_job = Job(id=2,
                                name='not_ready_job',
                                job_type=JobType.RAW_DATA,
                                state=JobState.WAITING,
                                workflow_id=1,
                                project_id=1)
            ready_job_start_failed = Job(id=3,
                                         name='ready_failed_job',
                                         job_type=JobType.RAW_DATA,
                                         state=JobState.WAITING,
                                         workflow_id=1,
                                         project_id=1)
            session.add_all([ready_job, not_ready_job, ready_job_start_failed])
            session.commit()

        def fake_start_job_if_ready(session, job):
            if job.name == ready_job_start_failed.name:
                job.error_message = 'Failed to start'
                return True, job.error_message
            if job.name == ready_job.name:
                return True, None
            if job.name == not_ready_job.name:
                return False, None
            raise RuntimeError(f'Unknown job {job.name}')

        mock_start_job_if_ready.side_effect = fake_start_job_if_ready

        runner = JobScheduler()
        context = RunnerContext(0, RunnerInput())
        status, output = runner.run(context)
        self.assertEqual(status, RunnerStatus.DONE)
        self.assertEqual(
            output,
            RunnerOutput(job_scheduler_output=JobSchedulerOutput(started_jobs=[ready_job.id],
                                                                 failed_to_start_jobs=[ready_job_start_failed.id],
                                                                 messages={
                                                                     ready_job_start_failed.id: 'Failed to start',
                                                                 })))


if __name__ == '__main__':
    unittest.main()
