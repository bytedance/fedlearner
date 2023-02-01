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

# pylint: disable=protected-access
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import DataBatch, ResourceState, Dataset, DatasetJob, \
    DatasetJobKind, DatasetJobSchedulerState, DatasetJobStage, DatasetJobState, DatasetKindV2, DatasetType
from fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor import CronDatasetJobExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.proto import dataset_pb2
from testing.no_web_server_test_case import NoWebServerTestCase


class CronDatasetJobExecutorTest(NoWebServerTestCase):
    _PROJECT_ID = 1
    _WORKFLOW_ID = 1
    _INPUT_DATASET_ID = 1
    _OUTPUT_DATASET_ID = 2

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
        cron_dataset_job_executor = CronDatasetJobExecutor()
        self.assertEqual(cron_dataset_job_executor.get_item_ids(), [1])


    @patch(
        'fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.CronDatasetJobExecutor.'\
            '_get_next_event_time'
    )
    @patch('fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.CronDatasetJobExecutor._should_run')
    def test_run_item(self, mock_should_run: MagicMock, mock_get_next_event_time: MagicMock):
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
                                     is_published=True)
            session.add(output_dataset)
            session.commit()

        cron_dataset_job_executor = CronDatasetJobExecutor()

        # test next_event_time bigger than now
        mock_should_run.return_value = True
        mock_get_next_event_time.return_value = datetime(2100, 1, 1)
        executor_result = cron_dataset_job_executor.run_item(item_id=1)
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        mock_get_next_event_time.assert_called_once()

        # test should_run is false
        mock_should_run.reset_mock()
        mock_get_next_event_time.reset_mock()
        mock_should_run.return_value = False
        mock_get_next_event_time.return_value = datetime(2022, 1, 1)
        executor_result = cron_dataset_job_executor.run_item(item_id=1)
        self.assertEqual(executor_result, ExecutorResult.SKIP)
        mock_get_next_event_time.assert_called_once()
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.get_context().scheduler_message, '数据批次20220101检查失败，请确认该批次命名格式及状态')

        # test should_run is True
        mock_should_run.reset_mock()
        mock_get_next_event_time.reset_mock()
        mock_should_run.return_value = True
        mock_get_next_event_time.return_value = datetime(2022, 1, 1)
        executor_result = cron_dataset_job_executor.run_item(item_id=1)
        self.assertEqual(executor_result, ExecutorResult.SUCCEEDED)
        mock_get_next_event_time.assert_called_once()

        with db.session_scope() as session:
            data_batch = session.query(DataBatch).get(1)
            self.assertEqual(data_batch.event_time, datetime(2022, 1, 1))
            dataset_job_stage = session.query(DatasetJobStage).get(1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1))
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.event_time, datetime(2022, 1, 1))
            self.assertEqual(dataset_job.get_context().scheduler_message, '已成功发起20220101批次处理任务')

    @patch('fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.get_oldest_hourly_folder_time')
    @patch('fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.get_oldest_daily_folder_time')
    def test_get_next_event_time(self, mock_get_oldest_daily_folder_time: MagicMock,
                                 mock_get_oldest_hourly_folder_time: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
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
            session.add(dataset_job)
            input_dataset = Dataset(id=self._INPUT_DATASET_ID,
                                    uuid='dataset_uuid',
                                    name='default dataset',
                                    dataset_type=DatasetType.STREAMING,
                                    comment='test comment',
                                    path='/data/dataset/123',
                                    project_id=self._PROJECT_ID,
                                    dataset_kind=DatasetKindV2.SOURCE,
                                    is_published=True)
            session.add(input_dataset)
            session.commit()
        cron_dataset_job_executor = CronDatasetJobExecutor()
        with db.session_scope() as session:
            # test input_dataset is source
            mock_get_oldest_daily_folder_time.return_value = datetime(2022, 8, 1)
            dataset_job = session.query(DatasetJob).get(1)
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            mock_get_oldest_daily_folder_time.assert_called_once_with('/data/dataset/123')
            self.assertEqual(next_event_time, datetime(2022, 8, 1))

            # test input_dataset is not source but has no batch
            mock_get_oldest_daily_folder_time.reset_mock()
            dataset_job.input_dataset.dataset_kind = DatasetKindV2.RAW
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            mock_get_oldest_daily_folder_time.assert_not_called()
            self.assertIsNone(next_event_time)

            # test input_dataset is not source and has batch
            data_batch_1 = DataBatch(id=1,
                                     name='20220801',
                                     dataset_id=self._INPUT_DATASET_ID,
                                     path='/data/test/batch/20220801',
                                     event_time=datetime(2022, 8, 1))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='20220802',
                                     dataset_id=self._INPUT_DATASET_ID,
                                     path='/data/test/batch/20220802',
                                     event_time=datetime(2022, 8, 2))
            session.add(data_batch_2)
            session.flush()
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            self.assertEqual(next_event_time, datetime(2022, 8, 1))

            # test dataset_job already has event_time
            dataset_job.event_time = datetime(2022, 8, 1)
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            self.assertEqual(next_event_time, datetime(2022, 8, 2))

        # test hourly level
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.time_range = timedelta(hours=1)
            session.commit()
        with db.session_scope() as session:
            # test input_dataset is source
            mock_get_oldest_hourly_folder_time.return_value = datetime(2022, 8, 1, 8)
            dataset_job = session.query(DatasetJob).get(1)
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            mock_get_oldest_hourly_folder_time.assert_called_once_with('/data/dataset/123')
            self.assertEqual(next_event_time, datetime(2022, 8, 1, 8))

            # test input_dataset is not source and has batch
            data_batch_1 = DataBatch(id=1,
                                     name='20220801',
                                     dataset_id=self._INPUT_DATASET_ID,
                                     path='/data/test/batch/20220801',
                                     event_time=datetime(2022, 8, 1, 8))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='20220802',
                                     dataset_id=self._INPUT_DATASET_ID,
                                     path='/data/test/batch/20220802',
                                     event_time=datetime(2022, 8, 1, 9))
            session.add(data_batch_2)
            session.flush()
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            self.assertEqual(next_event_time, datetime(2022, 8, 1, 8))

            # test dataset_job already has event_time
            dataset_job.event_time = datetime(2022, 8, 1, 8)
            next_event_time = cron_dataset_job_executor._get_next_event_time(session=session,
                                                                             runnable_dataset_job=dataset_job)
            self.assertEqual(next_event_time, datetime(2022, 8, 1, 9))

    @patch('fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor.check_batch_folder_ready')
    @patch('fedlearner_webconsole.dataset.models.DataBatch.get_frontend_state')
    def test_should_run(self, mock_get_frontend_state: MagicMock, mock_check_batch_folder_ready: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job uuid',
                                     project_id=self._PROJECT_ID,
                                     input_dataset_id=self._INPUT_DATASET_ID,
                                     output_dataset_id=self._OUTPUT_DATASET_ID,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING,
                                     coordinator_id=0,
                                     workflow_id=0,
                                     scheduler_state=DatasetJobSchedulerState.RUNNABLE,
                                     time_range=timedelta(days=1))
            dataset_job.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()}))
            session.add(dataset_job)
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
            data_batch = DataBatch(id=1,
                                   name='20220701',
                                   dataset_id=self._INPUT_DATASET_ID,
                                   path='/data/test/batch/20220701',
                                   event_time=datetime.strptime('20220701', '%Y%m%d'),
                                   file_size=100,
                                   num_example=10,
                                   num_feature=3,
                                   latest_parent_dataset_job_stage_id=1)
            session.add(data_batch)
            session.commit()

        cron_dataset_job_executor = CronDatasetJobExecutor()

        # test dataset
        with db.session_scope() as session:
            # test no data_batch
            dataset_job = session.query(DatasetJob).get(1)
            mock_get_frontend_state.return_value = ResourceState.SUCCEEDED
            self.assertFalse(cron_dataset_job_executor._should_run(session, dataset_job, datetime(2022, 7, 2)))
            mock_get_frontend_state.reset_mock()
            # test data_batch frontend state not succeeded
            mock_get_frontend_state.return_value = ResourceState.FAILED
            self.assertFalse(cron_dataset_job_executor._should_run(session, dataset_job, datetime(2022, 7, 1)))
            mock_get_frontend_state.reset_mock()
            # test should run
            mock_get_frontend_state.return_value = ResourceState.SUCCEEDED
            self.assertTrue(cron_dataset_job_executor._should_run(session, dataset_job, datetime(2022, 7, 1)))
            mock_check_batch_folder_ready.assert_not_called()
            mock_get_frontend_state.reset_mock()

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.input_dataset.dataset_kind = DatasetKindV2.SOURCE
            session.flush()
            # test streaming_folder not ready
            mock_check_batch_folder_ready.return_value = False
            self.assertFalse(cron_dataset_job_executor._should_run(session, dataset_job, datetime(2022, 7, 1)))
            mock_check_batch_folder_ready.assert_called_once_with(folder='/data/dataset/123', batch_name='20220701')
            mock_check_batch_folder_ready.reset_mock()
            # test should run
            mock_check_batch_folder_ready.return_value = True
            self.assertTrue(cron_dataset_job_executor._should_run(session, dataset_job, datetime(2022, 7, 1)))
            mock_check_batch_folder_ready.assert_called_once_with(folder='/data/dataset/123', batch_name='20220701')
            mock_get_frontend_state.assert_not_called()


if __name__ == '__main__':
    unittest.main()
