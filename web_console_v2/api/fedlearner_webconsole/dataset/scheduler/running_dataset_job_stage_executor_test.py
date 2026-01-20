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
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor import RunningDatasetJobStageExecutor
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, DatasetFormat, DatasetJob, DatasetJobKind, \
    DatasetJobSchedulerState, DatasetJobStage, DatasetJobState, DatasetKindV2, DatasetType, ResourceState
from fedlearner_webconsole.dataset.consts import ERROR_BATCH_SIZE
from fedlearner_webconsole.flag.models import _Flag
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.composer.models import RunnerStatus, SchedulerRunner
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.workflow.models import Workflow, WorkflowExternalState, WorkflowState
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.proto import dataset_pb2, service_pb2
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupParameter, CleanupPayload
from fedlearner_webconsole.proto.composer_pb2 import BatchStatsInput, RunnerInput
from testing.no_web_server_test_case import NoWebServerTestCase


def mock_process_pending_dataset_job_stage(self, session: Session,
                                           dataset_job_stage: DatasetJobStage) -> ExecutorResult:
    if dataset_job_stage.id == 1:
        return ExecutorResult.SKIP
    if dataset_job_stage.id == 2:
        dataset_job_stage.state = DatasetJobState.SUCCEEDED
        return ExecutorResult.SUCCEEDED
    dataset_job_stage.state = DatasetJobState.FAILED
    return ExecutorResult.SUCCEEDED


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
            participant = Participant(id=self._PARTICIPANT_ID,
                                      name='participant_1',
                                      domain_name='fl-fake_domain_name_1.com')
            project_participant = ProjectParticipant(project_id=self._PROJECT_ID, participant_id=self._PARTICIPANT_ID)
            session.add_all([participant, project_participant])
            session.commit()

    def _insert_psi_dataset_job_and_stage(self, state: DatasetJobState, job_id: int):
        with db.session_scope() as session:
            psi_dataset_job = DatasetJob(id=job_id,
                                         uuid=f'psi dataset_job uuid {job_id}',
                                         project_id=self._PROJECT_ID,
                                         input_dataset_id=self._INPUT_DATASET_ID,
                                         output_dataset_id=self._PSI_OUTPUT_DATASET_ID,
                                         kind=DatasetJobKind.DATA_ALIGNMENT,
                                         state=state,
                                         scheduler_state=DatasetJobSchedulerState.STOPPED,
                                         coordinator_id=0,
                                         workflow_id=0)
            psi_dataset_job_stage = DatasetJobStage(id=job_id,
                                                    uuid=f'psi dataset_job_stage uuid {job_id}',
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
                                               uuid=f'streaming dataset_job uuid {job_id}',
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
                                                          uuid=f'streaming dataset_job_stage uuid {job_id}',
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
        executor = RunningDatasetJobStageExecutor()
        processed_dataset_job_stage_ids = executor.get_item_ids()
        self.assertEqual(processed_dataset_job_stage_ids, [dataset_job_stage_running_id])

    @patch(
        'fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.RunningDatasetJobStageExecutor' \
            '._process_running_dataset_job_stage', mock_process_pending_dataset_job_stage
    )
    @patch(
        'fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.RunningDatasetJobStageExecutor' \
            '._process_succeeded_dataset_job_stage'
    )
    @patch(
        'fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.RunningDatasetJobStageExecutor' \
            '._process_failed_dataset_job_stage'
    )
    def test_run_item_not_running(self, mock_process_failed_dataset_job_stage: MagicMock,
                                  mock_process_succeeded_dataset_job_stage: MagicMock):
        dataset_job_stage_running_1_id = 1
        dataset_job_stage_running_2_id = 2
        dataset_job_stage_running_3_id = 3
        dataset_job_stage_pending_id = 4
        self._insert_psi_dataset_job_and_stage(DatasetJobState.PENDING, dataset_job_stage_pending_id)
        self._insert_psi_dataset_job_and_stage(DatasetJobState.RUNNING, dataset_job_stage_running_1_id)
        self._insert_psi_dataset_job_and_stage(DatasetJobState.RUNNING, dataset_job_stage_running_2_id)
        self._insert_psi_dataset_job_and_stage(DatasetJobState.RUNNING, dataset_job_stage_running_3_id)
        executor = RunningDatasetJobStageExecutor()

        # test not running
        executor_result = executor.run_item([dataset_job_stage_pending_id])
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        mock_process_succeeded_dataset_job_stage.assert_not_called()
        mock_process_failed_dataset_job_stage.assert_not_called()

        # test skip
        executor_result = executor.run_item([dataset_job_stage_running_1_id])
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        mock_process_succeeded_dataset_job_stage.assert_not_called()
        mock_process_failed_dataset_job_stage.assert_not_called()

        # test succeeded
        executor_result = executor.run_item([dataset_job_stage_running_2_id])
        self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
        mock_process_succeeded_dataset_job_stage.assert_called_once()
        mock_process_failed_dataset_job_stage.assert_not_called()
        mock_process_succeeded_dataset_job_stage.reset_mock()

        # test failed
        executor_result = executor.run_item([dataset_job_stage_running_3_id])
        self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
        mock_process_succeeded_dataset_job_stage.assert_not_called()
        mock_process_failed_dataset_job_stage.assert_called_once()

    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.ComposerService.'\
        'collect_v2')
    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.'\
        'RunningDatasetJobStageExecutor._need_batch_stats')
    @patch('fedlearner_webconsole.workflow.models.Workflow.get_state_for_frontend')
    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.ComposerService.'\
        'get_recent_runners')
    def test_process_running_dataset_job_stage(self, mock_get_recent_runners: MagicMock,
                                               mock_get_state_for_frontend: MagicMock, mock_need_batch_stats: MagicMock,
                                               mock_collect_v2: MagicMock):
        dataset_job_stage_running_id = 1
        self._insert_streaming_dataset_job_and_stage(DatasetJobState.RUNNING, dataset_job_stage_running_id)
        executor = RunningDatasetJobStageExecutor()

        # test workflow failed
        mock_get_state_for_frontend.return_value = WorkflowExternalState.FAILED
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_running_id)
            # pylint: disable=protected-access
            executor._process_running_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.FAILED)

        mock_get_recent_runners.reset_mock()
        mock_need_batch_stats.reset_mock()
        mock_get_state_for_frontend.reset_mock()

        # test no need batch stats
        mock_need_batch_stats.return_value = False
        mock_get_state_for_frontend.return_value = WorkflowExternalState.COMPLETED
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_running_id)
            # pylint: disable=protected-access
            executor._process_running_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.SUCCEEDED)

        mock_get_recent_runners.reset_mock()
        mock_need_batch_stats.reset_mock()
        mock_get_state_for_frontend.reset_mock()

        # test need batch stats and runner done
        mock_need_batch_stats.return_value = True
        mock_get_state_for_frontend.return_value = WorkflowExternalState.COMPLETED
        mock_get_recent_runners.return_value = [SchedulerRunner(status=RunnerStatus.DONE.value)]
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_running_id)
            dataset_job_stage.set_context(dataset_pb2.DatasetJobStageContext(batch_stats_item_name='123'))
            # pylint: disable=protected-access
            executor._process_running_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.SUCCEEDED)

        mock_get_recent_runners.reset_mock()
        mock_need_batch_stats.reset_mock()
        mock_get_state_for_frontend.reset_mock()

        # test need batch stats and runner failed
        mock_need_batch_stats.return_value = True
        mock_get_state_for_frontend.return_value = WorkflowExternalState.COMPLETED
        mock_get_recent_runners.return_value = [SchedulerRunner(status=RunnerStatus.FAILED.value)]
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_running_id)
            dataset_job_stage.set_context(dataset_pb2.DatasetJobStageContext(batch_stats_item_name='123'))
            # pylint: disable=protected-access
            executor._process_running_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.SUCCEEDED)
            mock_get_recent_runners.assert_called_once_with('123', count=1)
            batch = session.query(DataBatch).get(self._DATA_BATCH_WITH_EVENT_TIME_ID)
            self.assertEqual(batch.file_size, ERROR_BATCH_SIZE)

        mock_get_recent_runners.reset_mock()
        mock_need_batch_stats.reset_mock()
        mock_get_state_for_frontend.reset_mock()

        # test need batch stats and runner running
        mock_need_batch_stats.return_value = True
        mock_get_state_for_frontend.return_value = WorkflowExternalState.COMPLETED
        mock_get_recent_runners.return_value = [SchedulerRunner(status=RunnerStatus.RUNNING.value)]
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_running_id)
            dataset_job_stage.set_context(dataset_pb2.DatasetJobStageContext(batch_stats_item_name='123'))
            # pylint: disable=protected-access
            executor._process_running_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.RUNNING)

        mock_get_recent_runners.reset_mock()
        mock_need_batch_stats.reset_mock()
        mock_get_state_for_frontend.reset_mock()

        # test no runner
        mock_need_batch_stats.return_value = True
        mock_get_state_for_frontend.return_value = WorkflowExternalState.COMPLETED
        mock_get_recent_runners.return_value = []
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_running_id)
            # pylint: disable=protected-access
            executor._process_running_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.RUNNING)
            runner_input = RunnerInput(batch_stats_input=BatchStatsInput(batch_id=self._DATA_BATCH_WITH_EVENT_TIME_ID))
            mock_collect_v2.assert_called_once_with(
                name=f'batch_stats_{self._DATA_BATCH_WITH_EVENT_TIME_ID}_{dataset_job_stage_running_id}',
                items=[(ItemType.BATCH_STATS, runner_input)])

    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.'\
        'RunningDatasetJobStageExecutor._create_transaction')
    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.'\
        'RunningDatasetJobStageExecutor._delete_side_output')
    def test_process_succeeded_dataset_job_stage(self, mock_create_transaction: MagicMock,
                                                 mock_delete_side_output: MagicMock):
        dataset_job_stage_succeeded_id = 1
        self._insert_streaming_dataset_job_and_stage(DatasetJobState.SUCCEEDED, dataset_job_stage_succeeded_id)
        executor = RunningDatasetJobStageExecutor()

        # test no need publish
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_succeeded_id)
            dataset_job_stage.dataset_job.output_dataset.dataset_kind = DatasetKindV2.RAW
            # pylint: disable=protected-access
            executor._process_succeeded_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertFalse(dataset_job_stage.dataset_job.output_dataset.is_published)
            mock_create_transaction.assert_called_once()
            mock_delete_side_output.assert_called_once()

        mock_create_transaction.reset_mock()
        mock_delete_side_output.reset_mock()

        # test need publish
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_succeeded_id)
            dataset_job_stage.dataset_job.output_dataset.dataset_kind = DatasetKindV2.RAW
            dataset_job_stage.dataset_job.output_dataset.set_meta_info(dataset_pb2.DatasetMetaInfo(need_publish=True))
            # pylint: disable=protected-access
            executor._process_succeeded_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            self.assertTrue(dataset_job_stage.dataset_job.output_dataset.is_published)
            self.assertFalse(dataset_job_stage.dataset_job.output_dataset.get_meta_info().need_publish)
            mock_create_transaction.assert_called_once()
            mock_delete_side_output.assert_called_once()

    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.'\
        'RunningDatasetJobStageExecutor._delete_side_output')
    def test_process_failed_dataset_job_stage(self, mock_delete_side_output: MagicMock):
        dataset_job_stage_failed_id = 1
        self._insert_streaming_dataset_job_and_stage(DatasetJobState.FAILED, dataset_job_stage_failed_id)
        executor = RunningDatasetJobStageExecutor()

        # test failed dataset_job_stage
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_failed_id)
            # pylint: disable=protected-access
            executor._process_failed_dataset_job_stage(session=session, dataset_job_stage=dataset_job_stage)
            mock_delete_side_output.assert_called_once()

    @patch('fedlearner_webconsole.project.models.Project.get_storage_root_path')
    @patch('fedlearner_webconsole.cleanup.services.CleanupService.create_cleanup')
    @patch('fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor.now',
           lambda: datetime(2022, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc))
    def test_delete_side_output(self, cleanup_mock: MagicMock, mock_get_storage_root_path: MagicMock):
        dataset_job_stage_succeeded_id = 1
        self._insert_streaming_dataset_job_and_stage(DatasetJobState.SUCCEEDED, dataset_job_stage_succeeded_id)
        executor = RunningDatasetJobStageExecutor()
        mock_get_storage_root_path.return_value = '/data'

        # test normal dataset_job
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_succeeded_id)
            # pylint: disable=protected-access
            executor._delete_side_output(session=session, dataset_job_stage=dataset_job_stage)
            payload = CleanupPayload(paths=['/data/dataset/321/side_output/20220101'])
            cleanup_parmeter = CleanupParameter(resource_id=dataset_job_stage.id,
                                                resource_type='DATASET_JOB_STAGE',
                                                payload=payload,
                                                target_start_at=to_timestamp(
                                                    datetime(2022, 1, 2, 0, 0, 0, 0, tzinfo=timezone.utc)))
            cleanup_mock.assert_called_with(cleanup_parmeter=cleanup_parmeter)
        # test rsa_psi dataset_job
        cleanup_mock.reset_mock()
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_succeeded_id)
            dataset_job_stage.dataset_job.kind = DatasetJobKind.RSA_PSI_DATA_JOIN
            # pylint: disable=protected-access
            executor._delete_side_output(session=session, dataset_job_stage=dataset_job_stage)
            payload = CleanupPayload(paths=[
                '/data/dataset/321/side_output/20220101',
                '/data/raw_data/workflow_uuid-raw-data-job',
                '/data/data_source/workflow_uuid-psi-data-join-job/psi_output',
            ])
            cleanup_parmeter = CleanupParameter(resource_id=dataset_job_stage.id,
                                                resource_type='DATASET_JOB_STAGE',
                                                payload=payload,
                                                target_start_at=to_timestamp(
                                                    datetime(2022, 1, 2, 0, 0, 0, 0, tzinfo=timezone.utc)))
            cleanup_mock.assert_called_with(cleanup_parmeter=cleanup_parmeter)


if __name__ == '__main__':
    unittest.main()
