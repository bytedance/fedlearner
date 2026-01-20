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
from unittest.mock import PropertyMock, patch, MagicMock
from datetime import timedelta

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DatasetJobSchedulerState, \
    DatasetJobStage, DatasetJobState, DatasetKindV2, DatasetType
from fedlearner_webconsole.dataset.scheduler.dataset_job_executor import DatasetJobExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.job_configer.ot_psi_data_join_configer import OtPsiDataJoinConfiger
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.flag.models import _Flag
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.proto import dataset_pb2, project_pb2
from testing.no_web_server_test_case import NoWebServerTestCase


class DatasetJobExecutorTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _PARTICIPANT_ID = 1
    _WORKFLOW_ID = 1
    _INPUT_DATASET_ID = 1
    _OUTPUT_DATASET_ID = 2
    _DATASET_JOB_ID = 1

    def test_get_item_ids(self):
        with db.session_scope() as session:
            dataset_job_1 = DatasetJob(id=1,
                                       uuid='dataset_job_1',
                                       project_id=self._PROJECT_ID,
                                       input_dataset_id=self._INPUT_DATASET_ID,
                                       output_dataset_id=self._OUTPUT_DATASET_ID,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=0,
                                       workflow_id=self._WORKFLOW_ID,
                                       scheduler_state=DatasetJobSchedulerState.RUNNABLE,
                                       time_range=timedelta(days=1))
            dataset_job_1.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()}))
            session.add(dataset_job_1)
            dataset_job_2 = DatasetJob(id=2,
                                       uuid='dataset_job_2',
                                       project_id=self._PROJECT_ID,
                                       input_dataset_id=self._INPUT_DATASET_ID,
                                       output_dataset_id=3,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=0,
                                       workflow_id=self._WORKFLOW_ID,
                                       scheduler_state=DatasetJobSchedulerState.STOPPED,
                                       time_range=timedelta(days=1))
            dataset_job_2.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()}))
            session.add(dataset_job_2)
            dataset_job_3 = DatasetJob(id=3,
                                       uuid='dataset_job_3',
                                       project_id=self._PROJECT_ID,
                                       input_dataset_id=self._INPUT_DATASET_ID,
                                       output_dataset_id=4,
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=0,
                                       workflow_id=self._WORKFLOW_ID,
                                       scheduler_state=DatasetJobSchedulerState.PENDING,
                                       time_range=timedelta(days=1))
            dataset_job_3.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()}))
            session.add(dataset_job_3)
            session.commit()
        executor = DatasetJobExecutor()
        self.assertEqual(executor.get_item_ids(), [3])

    @patch('fedlearner_webconsole.flag.models.Flag.DATASET_AUTH_STATUS_CHECK_ENABLED', new_callable=PropertyMock)
    @patch('fedlearner_webconsole.dataset.scheduler.dataset_job_executor.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.dataset.local_controllers.DatasetJobStageLocalController.'\
        'create_data_batch_and_job_stage_as_coordinator')
    @patch('fedlearner_webconsole.dataset.scheduler.dataset_job_executor.RpcClient.create_dataset_job')
    def test_run_item(self, mock_create_dataset_job: MagicMock,
                      mock_create_data_batch_and_job_stage_as_coordinator: MagicMock, mock_list_flags: MagicMock,
                      mock_dataset_auth_status_check_enabled: MagicMock):
        with db.session_scope() as session:
            # pylint: disable=protected-access
            _insert_or_update_templates(session)
            dataset_job_1 = DatasetJob(id=self._PARTICIPANT_ID,
                                       uuid='dataset_job_1',
                                       project_id=self._PROJECT_ID,
                                       input_dataset_id=self._INPUT_DATASET_ID,
                                       output_dataset_id=self._OUTPUT_DATASET_ID,
                                       kind=DatasetJobKind.OT_PSI_DATA_JOIN,
                                       state=DatasetJobState.PENDING,
                                       coordinator_id=0,
                                       workflow_id=self._WORKFLOW_ID,
                                       scheduler_state=DatasetJobSchedulerState.RUNNABLE,
                                       time_range=timedelta(days=1))
            dataset_job_1.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(
                    global_configs={'test_participant_2': dataset_pb2.DatasetJobConfig()}))
            dataset_job_1.set_context(dataset_pb2.DatasetJobContext(has_stages=True))
            session.add(dataset_job_1)
            input_dataset = Dataset(id=self._INPUT_DATASET_ID,
                                    uuid='dataset_uuid',
                                    name='default dataset',
                                    dataset_type=DatasetType.STREAMING,
                                    comment='test comment',
                                    path='/data/dataset/123',
                                    project_id=self._PROJECT_ID,
                                    dataset_kind=DatasetKindV2.RAW,
                                    is_published=True)
            session.add(input_dataset)
            output_dataset = Dataset(id=self._OUTPUT_DATASET_ID,
                                     uuid='dataset_uuid',
                                     name='default dataset',
                                     dataset_type=DatasetType.STREAMING,
                                     comment='test comment',
                                     path='/data/dataset/123',
                                     project_id=self._PROJECT_ID,
                                     dataset_kind=DatasetKindV2.RAW,
                                     is_published=True,
                                     ticket_status=TicketStatus.APPROVED)
            participants_info = project_pb2.ParticipantsInfo(
                participants_map={
                    'test_participant_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'test_participant_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            output_dataset.set_participants_info(participants_info=participants_info)
            session.add(output_dataset)
            project = Project(id=self._PROJECT_ID, name='test-project')
            session.add(project)
            participant = Participant(id=self._PARTICIPANT_ID,
                                      name='participant_1',
                                      domain_name='fl-test_participant_2.com')
            project_participant = ProjectParticipant(project_id=self._PROJECT_ID, participant_id=self._PARTICIPANT_ID)
            session.add_all([participant, project_participant])
            session.commit()

        mock_list_flags.return_value = {'dataset_auth_status_check_enabled': True}
        mock_dataset_auth_status_check_enabled.return_value = _Flag('dataset_auth_status_check_enabled', False)
        executor = DatasetJobExecutor()
        # test not pending
        executor_result = executor.run_item(self._DATASET_JOB_ID)
        self.assertEqual(executor_result, ExecutorResult.SKIP)

        # test not approved
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.scheduler_state = DatasetJobSchedulerState.PENDING
            dataset_job.output_dataset.ticket_status = TicketStatus.PENDING
            session.commit()
        executor_result = executor.run_item(self._DATASET_JOB_ID)
        self.assertEqual(executor_result, ExecutorResult.SKIP)

        # test not coordinator
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.coordinator_id = 1
            dataset_job.output_dataset.ticket_status = TicketStatus.APPROVED
            session.commit()
        executor_result = executor.run_item(self._DATASET_JOB_ID)
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.STOPPED)
            mock_create_dataset_job.assert_not_called()

        # test streaming dataset_job and check flag True
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.coordinator_id = 0
            dataset_job.scheduler_state = DatasetJobSchedulerState.PENDING
            session.commit()
            session.flush()
            dataset_job_parameter = dataset_job.to_proto()
            dataset_job_parameter.workflow_definition.MergeFrom(OtPsiDataJoinConfiger(session).get_config())
        executor_result = executor.run_item(self._DATASET_JOB_ID)
        self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.RUNNABLE)
            participants_info = project_pb2.ParticipantsInfo(
                participants_map={
                    'test_participant_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'test_participant_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            mock_create_dataset_job.assert_called_once_with(
                dataset_job=dataset_job_parameter,
                ticket_uuid=None,
                dataset=dataset_pb2.Dataset(participants_info=participants_info))
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test_participant_2'].auth_status,
                AuthStatus.PENDING.name)

        mock_create_dataset_job.reset_mock()
        # test psi dataset_job need_create_batch
        mock_create_data_batch_and_job_stage_as_coordinator.return_value = DatasetJobStage(
            uuid='mock_stage',
            project_id=self._PROJECT_ID,
            coordinator_id=0,
            dataset_job_id=self._DATASET_JOB_ID,
            data_batch_id=0)
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.time_range = None
            dataset_job.scheduler_state = DatasetJobSchedulerState.PENDING
            dataset_job.output_dataset.dataset_type = DatasetType.PSI
            context = dataset_job.get_context()
            context.need_create_stage = True
            dataset_job.set_context(context)
            session.commit()
        executor_result = executor.run_item(self._DATASET_JOB_ID)
        self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.STOPPED)
            mock_create_dataset_job.assert_called_once()
            mock_create_data_batch_and_job_stage_as_coordinator.assert_called_once_with(
                dataset_job_id=self._DATASET_JOB_ID,
                global_configs=dataset_pb2.DatasetJobGlobalConfigs(
                    global_configs={'test_participant_2': dataset_pb2.DatasetJobConfig()}),
            )

        mock_create_dataset_job.reset_mock()
        mock_create_data_batch_and_job_stage_as_coordinator.reset_mock()
        mock_dataset_auth_status_check_enabled.reset_mock()
        # test check auth_status_failed
        mock_dataset_auth_status_check_enabled.return_value = _Flag('dataset_auth_status_check_enabled', True)
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            dataset_job.time_range = None
            dataset_job.scheduler_state = DatasetJobSchedulerState.PENDING
            dataset_job.output_dataset.dataset_type = DatasetType.PSI
            session.commit()
        executor_result = executor.run_item(self._DATASET_JOB_ID)
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(self._DATASET_JOB_ID)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.PENDING)
            mock_create_dataset_job.assert_called_once()
            self.assertEqual(
                dataset_job.output_dataset.get_participants_info().participants_map['test_participant_2'].auth_status,
                AuthStatus.PENDING.name)
            mock_create_data_batch_and_job_stage_as_coordinator.assert_not_called()


if __name__ == '__main__':
    unittest.main()
