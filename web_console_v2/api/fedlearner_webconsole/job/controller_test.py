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
from unittest.mock import MagicMock, patch, Mock, call

from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.controller import _start_job, schedule_job, stop_job, _are_peers_ready, \
    start_job_if_ready, create_job_without_workflow
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.job.yaml_formatter import YamlFormatterService
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.service_pb2 import CheckJobReadyResponse
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.utils.const import DEFAULT_OWNER_FOR_JOB_WITHOUT_WORKFLOW
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.workflow.models import Workflow  # pylint: disable=unused-import
from testing.no_web_server_test_case import NoWebServerTestCase


class ScheduleJobTest(NoWebServerTestCase):

    def test_schedule_job_disabled(self):
        with db.session_scope() as session:
            job = Job(id=1, is_disabled=True, state=JobState.NEW)
            schedule_job(session, job)
            # No change
            self.assertEqual(job.state, JobState.NEW)

    def test_schedule_job_invalid_state(self):
        with db.session_scope() as session:
            job = Job(id=1, state=JobState.STARTED)
            self.assertRaises(AssertionError, lambda: schedule_job(session, job))

    def test_schedule_job_successfully(self):
        with db.session_scope() as session:
            job = Job(id=1, state=JobState.NEW, snapshot='test snapshot')
            job.set_config(JobDefinition())
            schedule_job(session, job)
            self.assertIsNone(job.snapshot)
            self.assertEqual(job.state, JobState.WAITING)

    @patch('fedlearner_webconsole.job.controller.RpcClient.from_project_and_participant')
    def test_are_peers_ready(self, mock_rpc_client_factory: Mock):
        project_id = 1
        with db.session_scope() as session:
            participant_1 = Participant(id=1, name='participant 1', domain_name='p1.fedlearner.net')
            participant_2 = Participant(id=2, name='participant 2', domain_name='p2.fedlearner.net')
            project = Project(id=project_id, name='project 1')
            session.add_all([
                participant_1, participant_2, project,
                ProjectParticipant(project_id=1, participant_id=1),
                ProjectParticipant(project_id=1, participant_id=2)
            ])
            session.commit()

        mock_check_job_ready = MagicMock()
        mock_rpc_client_factory.return_value = MagicMock(check_job_ready=mock_check_job_ready)

        job_name = 'fake_job_name'
        with db.session_scope() as session:
            project = session.query(Project).get(project_id)
            # gRPC error
            mock_check_job_ready.side_effect = [
                CheckJobReadyResponse(status=common_pb2.Status(code=common_pb2.STATUS_UNKNOWN_ERROR)),
                CheckJobReadyResponse(is_ready=True)
            ]
            self.assertTrue(_are_peers_ready(session, project, job_name))
            mock_check_job_ready.assert_has_calls([call(job_name), call(job_name)])
            # Not ready
            mock_check_job_ready.side_effect = [
                CheckJobReadyResponse(is_ready=False),
                CheckJobReadyResponse(is_ready=True)
            ]
            self.assertFalse(_are_peers_ready(session, project, job_name))
            # Ready
            mock_check_job_ready.side_effect = [
                CheckJobReadyResponse(is_ready=True),
                CheckJobReadyResponse(is_ready=True)
            ]
            self.assertTrue(_are_peers_ready(session, project, job_name))


class StartJobTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.job.controller.YamlFormatterService', spec=YamlFormatterService)
    @patch('fedlearner_webconsole.job.controller.Job.build_crd_service')
    def test_start_job_successfully(self, mock_crd_service, mock_formatter_class):
        mock_formatter = mock_formatter_class.return_value
        mock_formatter.generate_job_run_yaml.return_value = 'fake job yaml'
        mock_crd_service.return_value = MagicMock(create_app=MagicMock(return_value=None))
        with db.session_scope() as session:
            job = Job(id=123,
                      name='test job',
                      job_type=JobType.RAW_DATA,
                      state=JobState.WAITING,
                      workflow_id=1,
                      project_id=1)
            session.add(job)
            session.commit()
            _start_job(session, job)
            session.commit()
        # Checks result
        mock_crd_service.return_value.create_app.assert_called_with('fake job yaml')
        with db.session_scope() as session:
            job = session.query(Job).get(123)
            self.assertEqual(job.state, JobState.STARTED)
            self.assertIsNone(job.error_message)

    @patch('fedlearner_webconsole.job.controller.YamlFormatterService', spec=YamlFormatterService)
    @patch('fedlearner_webconsole.job.controller.Job.build_crd_service')
    def test_start_job_exception(self, mock_crd_service, mock_formatter_class):
        mock_formatter = mock_formatter_class.return_value
        mock_formatter.generate_job_run_yaml.return_value = 'fake job yaml'
        mock_crd_service.return_value = MagicMock(create_app=MagicMock(return_value=None))
        mock_crd_service.return_value.create_app.side_effect = RuntimeError('some errors in k8s')
        with db.session_scope() as session:
            job = Job(id=123,
                      name='test job',
                      job_type=JobType.RAW_DATA,
                      state=JobState.WAITING,
                      workflow_id=1,
                      project_id=1)
            session.add(job)
            session.commit()
            _start_job(session, job)
            session.commit()
        # Checks result
        mock_crd_service.return_value.create_app.assert_called_with('fake job yaml')
        with db.session_scope() as session:
            job = session.query(Job).get(123)
            self.assertEqual(job.state, JobState.WAITING)
            self.assertEqual(job.error_message, 'some errors in k8s')


class StopJobTest(NoWebServerTestCase):

    def test_stop_job_invalid_state(self):
        with db.session_scope() as session:
            job = Job(id=1, state=JobState.NEW)
            stop_job(session, job)
            # No change
            self.assertEqual(job.state, JobState.NEW)

    @patch('fedlearner_webconsole.job.controller.Job.build_crd_service')
    @patch('fedlearner_webconsole.job.controller.JobService.set_status_to_snapshot')
    def test_stop_job_started(self, mock_set_status_to_snapshot: Mock, mock_build_crd_service: Mock):
        mock_delete_app = MagicMock()
        mock_build_crd_service.return_value = MagicMock(delete_app=mock_delete_app)

        with db.session_scope() as session:
            job = Job(id=1, name='test-job', state=JobState.STARTED, created_at=now())
            stop_job(session, job)
            mock_set_status_to_snapshot.assert_called_once_with(job)
            mock_delete_app.assert_called_once()
            self.assertEqual(job.state, JobState.STOPPED)

    def test_stop_job_waiting(self):
        with db.session_scope() as session:
            job = Job(id=1, name='test-job', state=JobState.WAITING, created_at=now())
            stop_job(session, job)
            self.assertEqual(job.state, JobState.NEW)

    def test_stop_job_completed(self):
        with db.session_scope() as session:
            job = Job(id=1, name='test-job', state=JobState.COMPLETED, created_at=now())
            stop_job(session, job)
            # No change
            self.assertEqual(job.state, JobState.COMPLETED)

    @patch('fedlearner_webconsole.job.controller._start_job')
    @patch('fedlearner_webconsole.job.controller._are_peers_ready')
    @patch('fedlearner_webconsole.job.controller.JobService.is_ready')
    def test_start_job_if_ready(self, mock_is_ready: Mock, mock_are_peers_ready: Mock, mock_start_job: Mock):
        with db.session_scope() as session:
            not_ready_job = Job(id=2,
                                name='not_ready_job',
                                job_type=JobType.RAW_DATA,
                                state=JobState.WAITING,
                                workflow_id=1,
                                project_id=1)
            mock_is_ready.return_value = False
            res = start_job_if_ready(session, not_ready_job)
            self.assertEqual(res, (False, None))
            peers_not_ready_job = Job(id=3,
                                      name='peers_not_ready_job',
                                      job_type=JobType.PSI_DATA_JOIN,
                                      state=JobState.WAITING,
                                      workflow_id=1,
                                      project_id=1)
            mock_is_ready.return_value = True
            mock_are_peers_ready.return_value = False
            peers_not_ready_job.set_config(JobDefinition(is_federated=True))
            res = start_job_if_ready(session, peers_not_ready_job)
            self.assertEqual(res, (False, None))
            peers_ready_job = Job(id=4,
                                  name='peers_ready_job',
                                  job_type=JobType.PSI_DATA_JOIN,
                                  state=JobState.WAITING,
                                  workflow_id=1,
                                  project_id=1)
            mock_are_peers_ready.return_value = True
            peers_ready_job.set_config(JobDefinition(is_federated=True))
            res = start_job_if_ready(session, peers_ready_job)
            self.assertEqual(res, (True, None))
            running_job = Job(id=3002,
                              name='running_job',
                              job_type=JobType.RAW_DATA,
                              state=JobState.STARTED,
                              workflow_id=1,
                              project_id=1)
            running_job.set_config(JobDefinition(is_federated=True))
            res = start_job_if_ready(session, running_job)
            self.assertEqual(res, (False, 'Invalid job state: 3002 JobState.STARTED'))
            start_job_calls = [call[0][1].id for call in mock_start_job.call_args_list]
            self.assertCountEqual(start_job_calls, [peers_ready_job.id])

    def test_create_job_without_workflow(self):
        with db.session_scope() as session:
            project = Project(id=1, name='project 1')
            session.add(project)
            job_def = JobDefinition(name='lonely_job', job_type=JobDefinition.ANALYZER)
            job_def.yaml_template = """
            {
                "apiVersion": "sparkoperator.k8s.io/v1beta2",
                "kind": "SparkApplication",
                "metadata": {
                    "name": self.name,
                },
            }
            """
            job = create_job_without_workflow(
                session,
                job_def=job_def,
                project_id=1,
            )
            session.commit()
            self.assertEqual(job.crd_kind, 'SparkApplication')
            yaml = YamlFormatterService(session).generate_job_run_yaml(job)
            self.assertEqual(yaml['metadata']['labels']['owner'], DEFAULT_OWNER_FOR_JOB_WITHOUT_WORKFLOW)
        with db.session_scope() as session:
            job_def.yaml_template = """
            {
                "apiVersion": "sparkoperator.k8s.io/v1beta2",
                "kind": "SparkApplication",
                "metadata": {
                    "name": self.name,
                    "namespace": workflow.name
                },
                
            }
            """
            job = create_job_without_workflow(session, job_def=job_def, project_id=1)
            session.commit()
            self.assertEqual(job.crd_kind, 'SparkApplication')
            with self.assertRaisesRegex(ValueError, 'Invalid python dict placeholder error msg: workflow.name'):
                YamlFormatterService(session).generate_job_run_yaml(job)


if __name__ == '__main__':
    unittest.main()
