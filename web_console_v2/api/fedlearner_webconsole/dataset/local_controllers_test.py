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

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch, MagicMock

from testing.common import NoWebServerTestCase

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.dataset.local_controllers import DatasetJobStageLocalController
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, DatasetJob, DatasetJobKind, DatasetJobStage, \
    DatasetJobState, DatasetKindV2, DatasetType
from fedlearner_webconsole.utils.resource_name import resource_uuid


class DatasetJobStageLocalControllerTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.dataset.local_controllers.start_workflow_locally')
    @patch('fedlearner_webconsole.dataset.local_controllers.DatasetJobStageService.start_dataset_job_stage')
    def test_start(self, mock_start_dataset_job_stage: MagicMock, mock_start_workflow_locally: MagicMock):
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStage(uuid=resource_uuid(),
                                                project_id=1,
                                                workflow_id=1,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            DatasetJobStageLocalController(session=session).start(dataset_job_stage=dataset_job_stage)
            mock_start_workflow_locally.assert_called_once()
            mock_start_dataset_job_stage.assert_called_once_with(dataset_job_stage=dataset_job_stage)

    @patch('fedlearner_webconsole.dataset.local_controllers.stop_workflow_locally')
    @patch('fedlearner_webconsole.dataset.local_controllers.DatasetJobStageService.finish_dataset_job_stage')
    def test_stop(self, mock_finish_dataset_job_stage: MagicMock, mock_stop_workflow_locally: MagicMock):
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStage(uuid=resource_uuid(),
                                                project_id=1,
                                                workflow_id=1,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            session.add(dataset_job_stage)

            dataset_job_stage_local_controller = DatasetJobStageLocalController(session=session)
            # test no worlflow
            dataset_job_stage_local_controller.stop(dataset_job_stage=dataset_job_stage)
            mock_stop_workflow_locally.assert_not_called()
            mock_finish_dataset_job_stage.assert_called_once_with(dataset_job_stage=dataset_job_stage,
                                                                  finish_state=DatasetJobState.STOPPED)

            # test has workflow
            mock_stop_workflow_locally.reset_mock()
            mock_finish_dataset_job_stage.reset_mock()
            workflow = Workflow(id=1)
            session.add(workflow)
            session.flush()
            dataset_job_stage_local_controller.stop(dataset_job_stage=dataset_job_stage)
            mock_stop_workflow_locally.assert_called_once()
            mock_finish_dataset_job_stage.assert_called_once_with(dataset_job_stage=dataset_job_stage,
                                                                  finish_state=DatasetJobState.STOPPED)

    def test_create_data_batch_and_job_stage(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING)
            dataset_job.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()}))
            session.add(dataset_job)
            output_dataset = Dataset(id=2,
                                     uuid='output_dataset uuid',
                                     name='output_dataset',
                                     dataset_type=DatasetType.PSI,
                                     comment='test comment',
                                     path='/data/dataset/123',
                                     project_id=1,
                                     dataset_kind=DatasetKindV2.PROCESSED)
            session.add(output_dataset)
            session.commit()

        # test PSI
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage(
                dataset_job_id=1)
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/0')

        # test PSI has batch
        with db.session_scope() as session:
            data_batch = DataBatch(id=1, name='test_data_batch', dataset_id=2, path='/data/test/batch/0')
            session.add(data_batch)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage(
                dataset_job_id=1)
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.data_batch.name, 'test_data_batch')
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/test/batch/0')

        # test PSI has batch and stage
        with db.session_scope() as session:
            data_batch = DataBatch(id=1, name='test_data_batch', dataset_id=2, path='/data/test/batch/0')
            session.add(data_batch)
            dataset_job_stage = DatasetJobStage(id=100,
                                                name='test_dataset_job',
                                                uuid='test_dataset_job uuid',
                                                project_id=1,
                                                workflow_id=0,
                                                dataset_job_id=1,
                                                data_batch_id=1)
            session.add(dataset_job_stage)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage(
                dataset_job_id=1, uuid='test_dataset_job uuid', name='test_dataset_job')
            self.assertEqual(dataset_job_stage.id, 100)

        with db.session_scope() as session:
            dataset = session.query(Dataset).get(2)
            dataset.dataset_type = DatasetType.STREAMING
            session.commit()

        # test STREAMING
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage(
                dataset_job_id=1, event_time=datetime(2022, 1, 1))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1).replace(tzinfo=timezone.utc))
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/20220101')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1))

        # test STREAMING has batch
        with db.session_scope() as session:
            data_batch_1 = DataBatch(id=1,
                                     name='test_data_batch 1',
                                     dataset_id=2,
                                     path='/data/test/batch/20220101',
                                     event_time=datetime(2022, 1, 1))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='test_data_batch 2',
                                     dataset_id=2,
                                     path='/data/test/batch/20220102',
                                     event_time=datetime(2022, 1, 2))
            session.add(data_batch_2)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage(
                dataset_job_id=1, event_time=datetime(2022, 1, 1))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1))
            self.assertEqual(dataset_job_stage.data_batch.name, 'test_data_batch 1')
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/test/batch/20220101')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1))

        # test STREAMING has batch and stage
        with db.session_scope() as session:
            data_batch_1 = DataBatch(id=1,
                                     name='test_data_batch 1',
                                     dataset_id=2,
                                     path='/data/test/batch/20220101',
                                     event_time=datetime(2022, 1, 1))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='test_data_batch 2',
                                     dataset_id=2,
                                     path='/data/test/batch/20220102',
                                     event_time=datetime(2022, 1, 2))
            session.add(data_batch_2)
            dataset_job_stage = DatasetJobStage(id=100,
                                                name='test_dataset_job',
                                                uuid='test_dataset_job uuid',
                                                project_id=1,
                                                workflow_id=0,
                                                dataset_job_id=1,
                                                data_batch_id=1,
                                                event_time=datetime(2022, 1, 2))
            session.add(dataset_job_stage)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage(
                dataset_job_id=1,
                event_time=datetime(2022, 1, 1),
                uuid='test_dataset_job uuid',
                name='test_dataset_job')
            self.assertEqual(dataset_job_stage.id, 100)

    def test_create_data_batch_and_job_stage_as_coordinator(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING)
            session.add(dataset_job)
            output_dataset = Dataset(id=2,
                                     uuid='output_dataset uuid',
                                     name='output_dataset',
                                     dataset_type=DatasetType.PSI,
                                     comment='test comment',
                                     path='/data/dataset/123',
                                     project_id=1,
                                     dataset_kind=DatasetKindV2.PROCESSED)
            session.add(output_dataset)
            session.commit()

        global_configs = dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()})
        # test PSI
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_coordinator(dataset_job_id=1,
                                                                                global_configs=global_configs)
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/0')
            self.assertEqual(dataset_job_stage.get_global_configs(), global_configs)
            self.assertTrue(dataset_job_stage.is_coordinator())

        # test PSI has batch
        with db.session_scope() as session:
            data_batch = DataBatch(id=1, name='test_data_batch', dataset_id=2, path='/data/test/batch/0')
            session.add(data_batch)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_coordinator(dataset_job_id=1,
                                                                                global_configs=global_configs)
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.data_batch.name, 'test_data_batch')
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/test/batch/0')
            self.assertEqual(dataset_job_stage.get_global_configs(), global_configs)
            self.assertTrue(dataset_job_stage.is_coordinator())

        with db.session_scope() as session:
            dataset = session.query(Dataset).get(2)
            dataset.dataset_type = DatasetType.STREAMING
            session.commit()

        # test STREAMING
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_coordinator(dataset_job_id=1,
                                                                                global_configs=global_configs,
                                                                                event_time=datetime(2022, 1, 1))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1).replace(tzinfo=timezone.utc))
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/20220101')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1))
            self.assertEqual(dataset_job_stage.get_global_configs(), global_configs)
            self.assertTrue(dataset_job_stage.is_coordinator())

        # test STREAMING has batch
        with db.session_scope() as session:
            data_batch_1 = DataBatch(id=1,
                                     name='test_data_batch 1',
                                     dataset_id=2,
                                     path='/data/test/batch/20220101',
                                     event_time=datetime(2022, 1, 1))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='test_data_batch 2',
                                     dataset_id=2,
                                     path='/data/test/batch/20220102',
                                     event_time=datetime(2022, 1, 2))
            session.add(data_batch_2)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_coordinator(dataset_job_id=1,
                                                                                global_configs=global_configs,
                                                                                event_time=datetime(2022, 1, 1))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1))
            self.assertEqual(dataset_job_stage.data_batch.name, 'test_data_batch 1')
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/test/batch/20220101')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1))
            self.assertEqual(dataset_job_stage.get_global_configs(), global_configs)
            self.assertTrue(dataset_job_stage.is_coordinator())

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.time_range = timedelta(hours=1)
            session.commit()

        # test STREAMING in hourly level
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_coordinator(dataset_job_id=1,
                                                                                global_configs=global_configs,
                                                                                event_time=datetime(2022, 1, 1, 8))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1, 8).replace(tzinfo=timezone.utc))
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/20220101-08')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1, 8))
            self.assertEqual(dataset_job_stage.get_global_configs(), global_configs)
            self.assertTrue(dataset_job_stage.is_coordinator())

    def test_create_data_batch_and_job_stage_as_participant(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING)
            session.add(dataset_job)
            output_dataset = Dataset(id=2,
                                     uuid='output_dataset uuid',
                                     name='output_dataset',
                                     dataset_type=DatasetType.PSI,
                                     comment='test comment',
                                     path='/data/dataset/123',
                                     project_id=1,
                                     dataset_kind=DatasetKindV2.PROCESSED)
            session.add(output_dataset)
            session.commit()

        # test PSI
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job')
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/0')
            self.assertIsNone(dataset_job_stage.global_configs)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)

        # test PSI has batch
        with db.session_scope() as session:
            data_batch = DataBatch(id=1, name='test_data_batch', dataset_id=2, path='/data/test/batch/0')
            session.add(data_batch)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job')
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertIsNone(dataset_job_stage.event_time)
            self.assertEqual(dataset_job_stage.data_batch.name, 'test_data_batch')
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/test/batch/0')
            self.assertIsNone(dataset_job_stage.global_configs)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)

        # test PSI has batch and stage
        with db.session_scope() as session:
            data_batch = DataBatch(id=1, name='test_data_batch', dataset_id=2, path='/data/test/batch/0')
            session.add(data_batch)
            dataset_job_stage = DatasetJobStage(id=100,
                                                name='test_dataset_job',
                                                uuid='test_dataset_job uuid',
                                                project_id=1,
                                                workflow_id=0,
                                                dataset_job_id=1,
                                                data_batch_id=1,
                                                coordinator_id=1)
            session.add(dataset_job_stage)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job')
            self.assertEqual(dataset_job_stage.id, 100)

        with db.session_scope() as session:
            dataset = session.query(Dataset).get(2)
            dataset.dataset_type = DatasetType.STREAMING
            session.commit()

        # test STREAMING
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job',
                                                                                event_time=datetime(2022, 1, 1))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1).replace(tzinfo=timezone.utc))
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/20220101')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1))
            self.assertIsNone(dataset_job_stage.global_configs)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)

        # test STREAMING has batch
        with db.session_scope() as session:
            data_batch_1 = DataBatch(id=1,
                                     name='test_data_batch 1',
                                     dataset_id=2,
                                     path='/data/test/batch/20220101',
                                     event_time=datetime(2022, 1, 1))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='test_data_batch 2',
                                     dataset_id=2,
                                     path='/data/test/batch/20220102',
                                     event_time=datetime(2022, 1, 2))
            session.add(data_batch_2)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job',
                                                                                event_time=datetime(2022, 1, 1))
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1))
            self.assertEqual(dataset_job_stage.data_batch.name, 'test_data_batch 1')
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/test/batch/20220101')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1))
            self.assertIsNone(dataset_job_stage.global_configs)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)

        # test STREAMING has batch and stage
        with db.session_scope() as session:
            data_batch_1 = DataBatch(id=1,
                                     name='test_data_batch 1',
                                     dataset_id=2,
                                     path='/data/test/batch/20220101',
                                     event_time=datetime(2022, 1, 1))
            session.add(data_batch_1)
            data_batch_2 = DataBatch(id=2,
                                     name='test_data_batch 2',
                                     dataset_id=2,
                                     path='/data/test/batch/20220102',
                                     event_time=datetime(2022, 1, 2))
            session.add(data_batch_2)
            dataset_job_stage = DatasetJobStage(id=100,
                                                name='test_dataset_job',
                                                uuid='test_dataset_job uuid',
                                                project_id=1,
                                                workflow_id=0,
                                                dataset_job_id=1,
                                                data_batch_id=1,
                                                event_time=datetime(2022, 1, 2),
                                                coordinator_id=1)
            session.add(dataset_job_stage)
            session.flush()
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                event_time=datetime(2022, 1, 1),
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job')
            self.assertEqual(dataset_job_stage.id, 100)

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.time_range = timedelta(hours=1)
            session.commit()

        # test STREAMING in hourly level
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageLocalController(
                session=session).create_data_batch_and_job_stage_as_participant(dataset_job_id=1,
                                                                                coordinator_id=1,
                                                                                event_time=datetime(2022, 1, 1, 8),
                                                                                uuid='test_dataset_job uuid',
                                                                                name='test_dataset_job')
            session.flush()
            self.assertEqual(dataset_job_stage.dataset_job_id, 1)
            self.assertEqual(dataset_job_stage.project_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(2022, 1, 1, 8).replace(tzinfo=timezone.utc))
            self.assertEqual(dataset_job_stage.data_batch.dataset_id, 2)
            self.assertEqual(dataset_job_stage.data_batch.path, '/data/dataset/123/batch/20220101-08')
            self.assertEqual(dataset_job_stage.data_batch.event_time, datetime(2022, 1, 1, 8))
            self.assertIsNone(dataset_job_stage.global_configs)
            self.assertEqual(dataset_job_stage.coordinator_id, 1)


if __name__ == '__main__':
    unittest.main()
