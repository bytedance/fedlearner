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
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import grpc

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor import PendingDatasetJobStageExecutor
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, DatasetJob, DatasetJobKind, \
    DatasetJobSchedulerState, DatasetJobStage, DatasetJobState, DatasetKindV2, DatasetType
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.proto.rpc.v2.job_service_pb2 import GetDatasetJobStageResponse
from testing.no_web_server_test_case import NoWebServerTestCase


class ProcessDatasetJobStagesTest(NoWebServerTestCase):

    _PROJECT_ID = 1
    _JOB_ID = 1
    _WORKFLOW_ID = 1
    _PARTICIPANT_ID = 1
    _INPUT_DATASET_ID = 1
    _STREAMING_OUTPUT_DATASET_ID = 2
    _PSI_OUTPUT_DATASET_ID = 3
    _DATA_BATCH_NO_EVENT_TIME_ID = 1
    _DATA_BATCH_WITH_EVENT_TIME_ID = 2

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            project = Project(id=self._PROJECT_ID, name='test-project')
            workflow = Workflow(id=self._WORKFLOW_ID,
                                project_id=self._PROJECT_ID,
                                state=WorkflowState.READY,
                                uuid='workflow_uuid')
            job = Job(id=self._JOB_ID,
                      state=JobState.NEW,
                      job_type=JobType.PSI_DATA_JOIN,
                      workflow_id=self._WORKFLOW_ID,
                      project_id=1)
            session.add_all([project, workflow, job])
            input_dataset = Dataset(id=self._INPUT_DATASET_ID,
                                    name='input dataset',
                                    path='/data/dataset/123',
                                    project_id=self._PROJECT_ID,
                                    created_at=datetime(2012, 1, 14, 12, 0, 6),
                                    dataset_kind=DatasetKindV2.RAW)
            streaming_output_dataset = Dataset(id=self._STREAMING_OUTPUT_DATASET_ID,
                                               name='streaming output dataset',
                                               uuid='streaming output_dataset uuid',
                                               path='/data/dataset/321',
                                               project_id=self._PROJECT_ID,
                                               created_at=datetime(2012, 1, 14, 12, 0, 7),
                                               dataset_kind=DatasetKindV2.PROCESSED,
                                               dataset_type=DatasetType.STREAMING)
            batch_with_event_time = DataBatch(id=self._DATA_BATCH_WITH_EVENT_TIME_ID,
                                              path='/data/dataset/321/batch/20220101',
                                              dataset_id=self._STREAMING_OUTPUT_DATASET_ID,
                                              event_time=datetime(2022, 1, 1))
            psi_output_dataset = Dataset(id=self._PSI_OUTPUT_DATASET_ID,
                                         name='psi output dataset',
                                         uuid='psi output_dataset uuid',
                                         path='/data/dataset/321',
                                         project_id=self._PROJECT_ID,
                                         created_at=datetime(2012, 1, 14, 12, 0, 7),
                                         dataset_kind=DatasetKindV2.PROCESSED,
                                         dataset_type=DatasetType.PSI)
            batch_no_event_time = DataBatch(id=self._DATA_BATCH_NO_EVENT_TIME_ID,
                                            path='/data/dataset/321/batch/0',
                                            dataset_id=self._PSI_OUTPUT_DATASET_ID)
            session.add_all([
                input_dataset, streaming_output_dataset, batch_with_event_time, psi_output_dataset, batch_no_event_time
            ])
            participant = Participant(id=self._PARTICIPANT_ID, name='participant_1', domain_name='fake_domain_name_1')
            project_participant = ProjectParticipant(project_id=self._PROJECT_ID, participant_id=self._PARTICIPANT_ID)
            session.add_all([participant, project_participant])
            session.commit()

    def _insert_psi_dataset_job_and_stage(self, state: DatasetJobState, job_id: int):
        with db.session_scope() as session:
            psi_dataset_job = DatasetJob(id=job_id,
                                         uuid=f'psi dataset_job uuid {state.name}',
                                         project_id=self._PROJECT_ID,
                                         input_dataset_id=self._INPUT_DATASET_ID,
                                         output_dataset_id=self._PSI_OUTPUT_DATASET_ID,
                                         kind=DatasetJobKind.DATA_ALIGNMENT,
                                         state=state,
                                         scheduler_state=DatasetJobSchedulerState.STOPPED,
                                         coordinator_id=0,
                                         workflow_id=0)
            psi_dataset_job_stage = DatasetJobStage(id=job_id,
                                                    uuid=f'psi dataset_job_stage uuid {state.name}',
                                                    name='psi dataset job stage',
                                                    project_id=self._PROJECT_ID,
                                                    workflow_id=self._WORKFLOW_ID,
                                                    dataset_job_id=job_id,
                                                    data_batch_id=self._DATA_BATCH_NO_EVENT_TIME_ID,
                                                    state=state)
            session.add_all([psi_dataset_job, psi_dataset_job_stage])
            session.commit()

    def _insert_streaming_dataset_job_and_stage(self, state: DatasetJobState, job_id: int):
        with db.session_scope() as session:
            streaming_dataset_job = DatasetJob(id=job_id,
                                               uuid=f'streaming dataset_job uuid {state.name}',
                                               project_id=self._PROJECT_ID,
                                               input_dataset_id=self._INPUT_DATASET_ID,
                                               output_dataset_id=self._STREAMING_OUTPUT_DATASET_ID,
                                               kind=DatasetJobKind.DATA_ALIGNMENT,
                                               state=state,
                                               scheduler_state=DatasetJobSchedulerState.STOPPED,
                                               coordinator_id=0,
                                               workflow_id=0,
                                               time_range=timedelta(days=1))
            streaming_dataset_job_stage = DatasetJobStage(id=job_id,
                                                          uuid=f'streaming dataset_job_stage uuid {state.name}',
                                                          name='streaming dataset job stage',
                                                          project_id=self._PROJECT_ID,
                                                          workflow_id=self._WORKFLOW_ID,
                                                          dataset_job_id=job_id,
                                                          data_batch_id=self._DATA_BATCH_WITH_EVENT_TIME_ID,
                                                          state=state,
                                                          event_time=datetime(2022, 1, 1))
            session.add_all([streaming_dataset_job, streaming_dataset_job_stage])
            session.commit()

    def test_get_item_ids(self):
        dataset_job_stage_pending_id = 1
        dataset_job_stage_running_id = 2
        dataset_job_stage_succeeded_id = 3
        self._insert_psi_dataset_job_and_stage(DatasetJobState.PENDING, dataset_job_stage_pending_id)
        self._insert_psi_dataset_job_and_stage(DatasetJobState.RUNNING, dataset_job_stage_running_id)
        self._insert_psi_dataset_job_and_stage(DatasetJobState.SUCCEEDED, dataset_job_stage_succeeded_id)
        executor = PendingDatasetJobStageExecutor()
        processed_dataset_job_stage_ids = executor.get_item_ids()
        self.assertEqual(processed_dataset_job_stage_ids, [dataset_job_stage_pending_id])

    @patch(
        'fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor.PendingDatasetJobStageExecutor.' \
            '_process_pending_dataset_job_stage'
    )
    @patch('fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor.DatasetJobStageController.'\
        'create_ready_workflow')
    def test_run_item(self, mock_create_ready_workflow: MagicMock, mock_process_pending_dataset_job_stage: MagicMock):
        dataset_job_stage_pending_id = 1
        dataset_job_stage_running_id = 2
        self._insert_psi_dataset_job_and_stage(DatasetJobState.PENDING, dataset_job_stage_pending_id)
        self._insert_psi_dataset_job_and_stage(DatasetJobState.RUNNING, dataset_job_stage_running_id)
        executor = PendingDatasetJobStageExecutor()

        # test not pending
        executor_result = executor.run_item([dataset_job_stage_running_id])
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        mock_create_ready_workflow.assert_not_called()
        mock_process_pending_dataset_job_stage.assert_not_called()

        # test succeeded
        mock_process_pending_dataset_job_stage.return_value = ExecutorResult.SUCCEEDED
        executor_result = executor.run_item([dataset_job_stage_pending_id])
        self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
        mock_create_ready_workflow.assert_not_called()
        mock_process_pending_dataset_job_stage.assert_called_once()
        self.assertEqual(mock_process_pending_dataset_job_stage.call_args[0][1].id, dataset_job_stage_pending_id)

        # test no workflow and process failed
        with db.session_scope() as session:
            dataset_job_stage_pending = session.query(DatasetJobStage).get(dataset_job_stage_pending_id)
            dataset_job_stage_pending.workflow_id = 0
            session.commit()
        mock_process_pending_dataset_job_stage.reset_mock()
        mock_process_pending_dataset_job_stage.return_value = ExecutorResult.FAILED
        executor_result = executor.run_item([dataset_job_stage_pending_id])
        self.assertEqual(executor_result, ExecutorResult.FAILED)
        mock_create_ready_workflow.assert_called_once()
        mock_process_pending_dataset_job_stage.assert_called_once()
        self.assertEqual(mock_process_pending_dataset_job_stage.call_args[0][1].id, dataset_job_stage_pending_id)

    @patch('fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor.JobServiceClient.'\
        'get_dataset_job_stage')
    @patch('fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor.JobServiceClient.'\
        'create_dataset_job_stage')
    @patch('fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor.DatasetJobStageController.'\
        'start')
    def test_process_pending_dataset_job_stage(self, mock_start: MagicMock, mock_create_dataset_job_stage: MagicMock,
                                               mock_get_dataset_job_stage: MagicMock):
        dataset_job_stage_pending_id = 1
        self._insert_streaming_dataset_job_and_stage(DatasetJobState.PENDING, dataset_job_stage_pending_id)
        executor = PendingDatasetJobStageExecutor()

        # test not coordinator
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_pending_id)
            dataset_job_stage.coordinator_id = 1
            # pylint: disable=protected-access
            executor_result = executor._process_pending_dataset_job_stage(session=session,
                                                                          dataset_job_stage=dataset_job_stage)
            self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
            mock_get_dataset_job_stage.assert_not_called()

        # test not_ready
        mock_get_dataset_job_stage.return_value = GetDatasetJobStageResponse(
            dataset_job_stage=dataset_pb2.DatasetJobStage(is_ready=False))
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_pending_id)
            # pylint: disable=protected-access
            executor_result = executor._process_pending_dataset_job_stage(session=session,
                                                                          dataset_job_stage=dataset_job_stage)
            self.assertEqual(executor_result, ExecutorResult.SKIP)
            mock_create_dataset_job_stage.assert_not_called()
            mock_start.assert_not_called()

        mock_get_dataset_job_stage.reset_mock()

        # test ready and start
        mock_get_dataset_job_stage.return_value = GetDatasetJobStageResponse(
            dataset_job_stage=dataset_pb2.DatasetJobStage(is_ready=True))
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_pending_id)
            # pylint: disable=protected-access
            executor_result = executor._process_pending_dataset_job_stage(session=session,
                                                                          dataset_job_stage=dataset_job_stage)
            self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
            mock_create_dataset_job_stage.assert_not_called()
            mock_start.assert_called_once_with(uuid='streaming dataset_job_stage uuid PENDING')

        mock_get_dataset_job_stage.reset_mock()
        mock_start.reset_mock()

        # test get_dataset_job_stage raise
        e = grpc.RpcError()
        e.code = lambda: grpc.StatusCode.NOT_FOUND
        mock_get_dataset_job_stage.side_effect = e
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_pending_id)
            # pylint: disable=protected-access
            executor_result = executor._process_pending_dataset_job_stage(session=session,
                                                                          dataset_job_stage=dataset_job_stage)
            self.assertEqual(executor_result, ExecutorResult.SKIP)
            mock_create_dataset_job_stage.assert_called_once_with(
                dataset_job_uuid='streaming dataset_job uuid PENDING',
                dataset_job_stage_uuid='streaming dataset_job_stage uuid PENDING',
                name='streaming dataset job stage',
                event_time=datetime(2022, 1, 1))
            mock_start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
