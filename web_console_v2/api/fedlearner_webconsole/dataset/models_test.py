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

from datetime import datetime, timedelta
import time
import unittest
from unittest.mock import MagicMock, PropertyMock, patch
from testing.common import NoWebServerTestCase

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import (DATASET_STATE_CONVERT_MAP_V2, Dataset, DataSource, DatasetFormat,
                                                  DatasetJobSchedulerState, DatasetJobStage, DatasetKindV2, ImportType,
                                                  PublishFrontendState, ResourceState, StoreFormat, DatasetType,
                                                  DatasetJob, DataSourceType, DatasetJobKind, DatasetJobState,
                                                  DataBatch)
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto import dataset_pb2, project_pb2
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobStageContext, DatasetMetaInfo, DatasetJobConfig, \
    DatasetJobGlobalConfigs, TimeRange
from google.protobuf.struct_pb2 import Value


class DataBatchTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset = Dataset(id=1,
                              uuid=resource_uuid(),
                              name='default dataset',
                              dataset_type=DatasetType.PSI,
                              comment='test comment',
                              path='/data/dataset/123',
                              project_id=1,
                              created_at=datetime(2012, 1, 14, 12, 0, 5),
                              dataset_kind=DatasetKindV2.RAW,
                              is_published=False,
                              import_type=ImportType.NO_COPY)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220701',
                                   dataset_id=1,
                                   path='/data/test/batch/20220701',
                                   event_time=datetime.strptime('20220701', '%Y%m%d'),
                                   file_size=100,
                                   num_example=10,
                                   num_feature=3,
                                   latest_parent_dataset_job_stage_id=1)
            session.add(data_batch)
            session.commit()

    def test_to_proto(self):
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).get(1)
            self.assertPartiallyEqual(
                to_dict(data_batch.to_proto()),
                {
                    'id': 1,
                    'name': '20220701',
                    'dataset_id': 1,
                    'path': '/data/test/batch/20220701',
                    'event_time': to_timestamp(datetime.strptime('20220701', '%Y%m%d')),
                    'file_size': 100,
                    'num_example': 10,
                    'num_feature': 3,
                    'comment': '',
                    'state': 'FAILED',
                    'latest_parent_dataset_job_stage_id': 1,
                    'latest_analyzer_dataset_job_stage_id': 0,
                },
                ignore_fields=['created_at', 'updated_at'],
            )

    def test_is_available(self):
        with db.session_scope() as session:
            job_stage = DatasetJobStage(id=1,
                                        uuid='job stage uuid',
                                        name='default dataset job stage',
                                        project_id=1,
                                        workflow_id=1,
                                        created_at=datetime(2012, 1, 14, 12, 0, 5),
                                        dataset_job_id=1,
                                        data_batch_id=1,
                                        event_time=datetime(2012, 1, 15),
                                        state=DatasetJobState.PENDING,
                                        coordinator_id=0)
            session.add(job_stage)
            session.commit()
        with db.session_scope() as session:
            data_batch = session.query(DataBatch).get(1)
            self.assertFalse(data_batch.is_available())
            job_stage = session.query(DatasetJobStage).get(1)
            job_stage.state = DatasetJobState.SUCCEEDED
            session.flush()
            self.assertTrue(data_batch.is_available())


class DatasetTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            default_dataset = Dataset(id=10,
                                      uuid=resource_uuid(),
                                      name='default dataset',
                                      dataset_type=DatasetType.PSI,
                                      comment='test comment',
                                      path='/data/dataset/123',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 5),
                                      dataset_kind=DatasetKindV2.RAW,
                                      is_published=False)
            session.add(default_dataset)
            session.commit()

    def test_dataset_meta_info(self):
        meta_info = DatasetMetaInfo(value=100)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            dataset.set_meta_info(meta_info)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            meta_info_current = dataset.get_meta_info()
            self.assertEqual(meta_info_current, meta_info)

    def test_get_frontend_state(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            for state, front_state in DATASET_STATE_CONVERT_MAP_V2.items():
                dataset.parent_dataset_job.state = state
                self.assertEqual(dataset.get_frontend_state(), front_state)

    def test_get_single_batch(self):
        # test no batch
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            with self.assertRaises(TypeError) as cm:
                dataset.get_single_batch()
            self.assertEqual(cm.exception.args[0], 'there is no data_batch for this dataset 10')

        # test one batch
        first_event_time = datetime(year=2000, month=1, day=1)
        with db.session_scope() as session:
            batch = DataBatch(dataset_id=10, event_time=first_event_time)
            session.add(batch)
            session.commit()

        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            batch = dataset.get_single_batch()
            self.assertEqual(batch.event_time, first_event_time)

        # test two batch
        second_event_time = datetime(year=2000, month=1, day=2)
        with db.session_scope() as session:
            batch = DataBatch(dataset_id=10, event_time=second_event_time)
            session.add(batch)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            with self.assertRaises(TypeError) as cm:
                dataset.get_single_batch()
            self.assertEqual(cm.exception.args[0], 'there is more than one data_batch for this dataset 10')

    def test_to_proto(self):
        participants_info = project_pb2.ParticipantsInfo(
            participants_map={
                'test_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                'test_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
            })
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(10)
            dataset.auth_status = AuthStatus.AUTHORIZED
            dataset.set_participants_info(participants_info)
            dataset_proto = dataset.to_proto()
            self.assertPartiallyEqual(
                to_dict(dataset_proto),
                {
                    'id': 10,
                    'project_id': 1,
                    'name': 'default dataset',
                    'path': '/data/dataset/123',
                    'comment': 'test comment',
                    'dataset_format': 'TABULAR',
                    'state_frontend': 'FAILED',
                    'dataset_kind': 'RAW',
                    'workflow_id': 0,
                    'data_source': '',
                    'file_size': 0,
                    'num_example': 0,
                    'num_feature': 0,
                    'deleted_at': 0,
                    'parent_dataset_job_id': 0,
                    'analyzer_dataset_job_id': 0,
                    'is_published': False,
                    'value': 0,
                    'schema_checkers': [],
                    'creator_username': '',
                    'import_type': 'COPY',
                    'dataset_type': 'PSI',
                    'store_format': 'TFRECORDS',
                    'publish_frontend_state': 'UNPUBLISHED',
                    'auth_frontend_state': 'AUTH_PENDING',
                    'local_auth_status': 'AUTHORIZED',
                    'participants_info': {
                        'participants_map': {
                            'test_1': {
                                'auth_status': 'PENDING',
                                'name': '',
                                'role': '',
                                'state': '',
                                'type': '',
                            },
                            'test_2': {
                                'auth_status': 'AUTHORIZED',
                                'name': '',
                                'role': '',
                                'state': '',
                                'type': '',
                            },
                        }
                    },
                },
                ignore_fields=['uuid', 'created_at', 'updated_at'],
            )

    def test_parent_dataset_job(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='dataset_job',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            micro_dataset_job = DatasetJob(id=2,
                                           uuid='micro_dataset_job',
                                           project_id=1,
                                           input_dataset_id=10,
                                           output_dataset_id=10,
                                           kind=DatasetJobKind.ANALYZER,
                                           state=DatasetJobState.SUCCEEDED)
            session.add(micro_dataset_job)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.parent_dataset_job.id, 1)

    def test_publish_frontend_state(self):
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.publish_frontend_state, PublishFrontendState.UNPUBLISHED)
            dataset.is_published = True
            dataset.ticket_status = TicketStatus.APPROVED
            self.assertEqual(dataset.publish_frontend_state, PublishFrontendState.PUBLISHED)
            dataset.ticket_status = TicketStatus.PENDING
            self.assertEqual(dataset.publish_frontend_state, PublishFrontendState.TICKET_PENDING)
            dataset.ticket_status = TicketStatus.DECLINED
            self.assertEqual(dataset.publish_frontend_state, PublishFrontendState.TICKET_DECLINED)

    def test_updated_at(self):
        with db.session_scope() as session:
            data_batch = DataBatch(id=1,
                                   name='20220701',
                                   dataset_id=10,
                                   path='/data/test/batch/20220701',
                                   event_time=datetime(2022, 7, 1),
                                   file_size=100,
                                   num_example=10,
                                   num_feature=3)
            session.add(data_batch)
            session.commit()
        # make sure two batch have different updated_at time
        time.sleep(1)
        with db.session_scope() as session:
            data_batch = DataBatch(id=2,
                                   name='20220702',
                                   dataset_id=10,
                                   path='/data/test/batch/20220702',
                                   event_time=datetime(2022, 7, 2),
                                   file_size=100,
                                   num_example=10,
                                   num_feature=3)
            session.add(data_batch)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            data_batch = session.query(DataBatch).get(2)
            self.assertEqual(dataset.to_proto().updated_at, to_timestamp(data_batch.updated_at))


class DataSourceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            default_datasource = DataSource(id=10,
                                            uuid=resource_uuid(),
                                            name='default dataset',
                                            dataset_type=DatasetType.PSI,
                                            comment='test comment',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5),
                                            is_published=False,
                                            creator_username='xiaohang',
                                            store_format=StoreFormat.CSV,
                                            dataset_format=DatasetFormat.TABULAR.value)
            default_datasource.set_meta_info(
                meta=DatasetMetaInfo(datasource_type=DataSourceType.HDFS.value, is_user_upload=False))
            session.add(default_datasource)
            session.commit()

    def test_to_data_source(self):
        with db.session_scope() as session:
            dataset = session.query(DataSource).get(10)
            data_source = dataset_pb2.DataSource(id=dataset.id,
                                                 uuid=dataset.uuid,
                                                 name=dataset.name,
                                                 type=DataSourceType.HDFS.value,
                                                 url=dataset.path,
                                                 created_at=to_timestamp(dataset.created_at),
                                                 project_id=dataset.project_id,
                                                 is_user_upload=False,
                                                 creator_username='xiaohang',
                                                 dataset_format='TABULAR',
                                                 store_format='CSV',
                                                 dataset_type='PSI',
                                                 comment='test comment')
            self.assertEqual(dataset.to_proto(), data_source)


class InternalProcessedDatasetTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            default_dataset = Dataset(id=10,
                                      uuid=resource_uuid(),
                                      name='default dataset',
                                      dataset_type=DatasetType.PSI,
                                      comment='test comment',
                                      path='/data/dataset/123',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 5),
                                      dataset_kind=DatasetKindV2.INTERNAL_PROCESSED,
                                      is_published=False,
                                      auth_status=AuthStatus.AUTHORIZED)
            session.add(default_dataset)
            session.commit()

    def test_get_frontend_state(self):
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.get_frontend_state(), ResourceState.SUCCEEDED)


class DatasetJobTest(NoWebServerTestCase):

    def test_get_set_global_configs(self):
        dataset_job = DatasetJob()
        global_configs = DatasetJobGlobalConfigs()
        global_configs.global_configs['test'].MergeFrom(
            DatasetJobConfig(dataset_uuid=resource_uuid(),
                             variables=[
                                 Variable(name='hello',
                                          value_type=Variable.ValueType.NUMBER,
                                          typed_value=Value(number_value=1)),
                                 Variable(name='test',
                                          value_type=Variable.ValueType.STRING,
                                          typed_value=Value(string_value='test_value')),
                             ]))
        dataset_job.set_global_configs(global_configs)
        new_global_configs = dataset_job.get_global_configs()
        self.assertEqual(new_global_configs, global_configs)

    @patch('fedlearner_webconsole.dataset.models.DatasetJob.output_dataset', new_callable=PropertyMock)
    def test_to_proto(self, mock_output_dataset: MagicMock):
        uuid = resource_uuid()
        current_time = now()
        dataset_job = DatasetJob(id=1,
                                 name='test_dataset_job',
                                 coordinator_id=2,
                                 uuid=uuid,
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING,
                                 created_at=current_time,
                                 updated_at=current_time,
                                 creator_username='test user',
                                 scheduler_state=DatasetJobSchedulerState.PENDING)
        global_configs = DatasetJobGlobalConfigs()
        global_configs.global_configs['test'].MergeFrom(
            DatasetJobConfig(dataset_uuid=resource_uuid(),
                             variables=[
                                 Variable(name='hello',
                                          value_type=Variable.ValueType.NUMBER,
                                          typed_value=Value(number_value=1)),
                                 Variable(name='test',
                                          value_type=Variable.ValueType.STRING,
                                          typed_value=Value(string_value='test_value')),
                             ]))
        dataset_job.set_global_configs(global_configs)
        dataset_job.set_scheduler_message(scheduler_message='调度信息 🐵')

        mock_output_dataset.return_value = None
        dataset_job_pb = dataset_pb2.DatasetJob(id=1,
                                                name='test_dataset_job',
                                                coordinator_id=2,
                                                uuid=uuid,
                                                project_id=1,
                                                kind=DatasetJobKind.DATA_ALIGNMENT.value,
                                                state=DatasetJobState.PENDING.value,
                                                global_configs=global_configs,
                                                created_at=to_timestamp(current_time),
                                                updated_at=to_timestamp(current_time),
                                                creator_username='test user',
                                                scheduler_state=DatasetJobSchedulerState.PENDING.name,
                                                time_range=TimeRange(),
                                                scheduler_message='调度信息 🐵')

        self.assertEqual(dataset_job.to_proto(), dataset_job_pb)

        dataset_job.workflow = Workflow(id=1, uuid='workflow_uuid')
        mock_output_dataset.return_value = Dataset(id=1, name='test_dataset', uuid='dataset_uuid')
        dataset_job.workflow_id = 1
        dataset_job.output_dataset_id = 1
        dataset_job_pb.is_ready = True
        dataset_job_pb.workflow_id = 1
        dataset_job_pb.result_dataset_name = 'test_dataset'
        dataset_job_pb.result_dataset_uuid = 'dataset_uuid'
        self.assertEqual(dataset_job.to_proto(), dataset_job_pb)

        context = dataset_job.get_context()
        context.input_data_batch_num_example = 1000
        context.output_data_batch_num_example = 500
        dataset_job.set_context(context)
        dataset_job_pb.input_data_batch_num_example = 1000
        dataset_job_pb.output_data_batch_num_example = 500
        self.assertEqual(dataset_job.to_proto(), dataset_job_pb)

    @patch('fedlearner_webconsole.dataset.models.DatasetJob.output_dataset', new_callable=PropertyMock)
    def test_to_ref(self, mock_output_dataset: MagicMock):
        uuid = resource_uuid()
        output_dataset = Dataset(name='test_output_dataset', id=1)
        dataset_job = DatasetJob(id=1,
                                 name='test_dataset_job',
                                 coordinator_id=2,
                                 uuid=uuid,
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING,
                                 output_dataset_id=1,
                                 created_at=now(),
                                 creator_username='test user')
        mock_output_dataset.return_value = output_dataset
        self.assertPartiallyEqual(to_dict(dataset_job.to_ref()), {
            'id': 1,
            'name': 'test_dataset_job',
            'coordinator_id': 2,
            'uuid': uuid,
            'project_id': 1,
            'kind': DatasetJobKind.DATA_ALIGNMENT.name,
            'state': DatasetJobState.PENDING.name,
            'result_dataset_id': 1,
            'result_dataset_name': 'test_output_dataset',
            'has_stages': False,
            'creator_username': 'test user',
        },
                                  ignore_fields=['created_at'])

    def test_is_finished(self):
        dataset_job = DatasetJob(uuid='uuid',
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING,
                                 input_dataset_id=1,
                                 output_dataset_id=2,
                                 created_at=now())
        self.assertFalse(dataset_job.is_finished())
        dataset_job.state = DatasetJobState.RUNNING
        self.assertFalse(dataset_job.is_finished())
        dataset_job.state = DatasetJobState.SUCCEEDED
        self.assertTrue(dataset_job.is_finished())
        dataset_job.state = DatasetJobState.FAILED
        self.assertTrue(dataset_job.is_finished())

    def test_is_cron(self):
        dataset_job = DatasetJob(id=1,
                                 name='test_dataset_job',
                                 coordinator_id=2,
                                 uuid='uuid',
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING)
        self.assertFalse(dataset_job.is_cron())
        dataset_job.time_range = timedelta(days=1)
        self.assertTrue(dataset_job.is_cron())

    def test_is_daily_cron(self):
        dataset_job = DatasetJob(id=1,
                                 name='test_dataset_job',
                                 coordinator_id=2,
                                 uuid='uuid',
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING)
        self.assertFalse(dataset_job.is_daily_cron())
        dataset_job.time_range = timedelta(days=1)
        self.assertTrue(dataset_job.is_daily_cron())
        dataset_job.time_range = timedelta(hours=1)
        self.assertFalse(dataset_job.is_daily_cron())

    def test_is_hourly_cron(self):
        dataset_job = DatasetJob(id=1,
                                 name='test_dataset_job',
                                 coordinator_id=2,
                                 uuid='uuid',
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING)
        self.assertFalse(dataset_job.is_hourly_cron())
        dataset_job.time_range = timedelta(days=1)
        self.assertFalse(dataset_job.is_hourly_cron())
        dataset_job.time_range = timedelta(hours=1)
        self.assertTrue(dataset_job.is_hourly_cron())

    def test_set_scheduler_message(self):
        scheduler_message = '调度信息 🦻'
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     name='test_dataset_job',
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     coordinator_id=0,
                                     uuid='uuid',
                                     project_id=1,
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.PENDING)
            dataset_job.set_scheduler_message(scheduler_message=scheduler_message)
            session.add(dataset_job)
            session.commit()

        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.get_context().scheduler_message, scheduler_message)


class DatasetJobStageTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset_job = DatasetJob(uuid='dataset_job uuid',
                                     project_id=1,
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.PENDING,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     created_at=now())
            session.add(dataset_job)
            job_stage = DatasetJobStage(id=1,
                                        uuid='uuid_1',
                                        name='default dataset job stage',
                                        project_id=1,
                                        workflow_id=1,
                                        created_at=datetime(2012, 1, 14, 12, 0, 5),
                                        dataset_job_id=1,
                                        data_batch_id=1,
                                        event_time=datetime(2012, 1, 15),
                                        state=DatasetJobState.PENDING,
                                        coordinator_id=0)
            session.add(job_stage)
            session.commit()

    def test_get_set_global_configs(self):
        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            global_configs = DatasetJobGlobalConfigs()
            global_configs.global_configs['test'].MergeFrom(
                DatasetJobConfig(dataset_uuid=resource_uuid(),
                                 variables=[
                                     Variable(name='hello',
                                              value_type=Variable.ValueType.NUMBER,
                                              typed_value=Value(number_value=1)),
                                     Variable(name='test',
                                              value_type=Variable.ValueType.STRING,
                                              typed_value=Value(string_value='test_value')),
                                 ]))
            job_stage.set_global_configs(global_configs)
            new_global_configs = job_stage.get_global_configs()
            self.assertEqual(new_global_configs, global_configs)

    def test_to_ref(self):
        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            job_stage_ref = job_stage.to_ref()
            self.assertEqual(
                to_dict(job_stage_ref), {
                    'id': 1,
                    'name': 'default dataset job stage',
                    'dataset_job_id': 1,
                    'output_data_batch_id': 1,
                    'project_id': 1,
                    'state': DatasetJobState.PENDING.name,
                    'created_at': to_timestamp(datetime(2012, 1, 14, 12, 0, 5)),
                    'kind': DatasetJobKind.DATA_ALIGNMENT.name,
                })

    def test_to_proto(self):
        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            context = DatasetJobStageContext(batch_stats_item_name='batch_stats_item_1',
                                             input_data_batch_num_example=100,
                                             output_data_batch_num_example=50,
                                             scheduler_message='错误信息 ✖️')
            job_stage.set_context(context=context)
            job_stage_proto = job_stage.to_proto()
            self.assertPartiallyEqual(
                to_dict(job_stage_proto),
                {
                    'id': 1,
                    'name': 'default dataset job stage',
                    'uuid': 'uuid_1',
                    'dataset_job_id': 1,
                    'output_data_batch_id': 1,
                    'workflow_id': 1,
                    'project_id': 1,
                    'state': DatasetJobState.PENDING.name,
                    'event_time': to_timestamp(datetime(2012, 1, 15)),
                    'created_at': to_timestamp(datetime(2012, 1, 14, 12, 0, 5)),
                    'dataset_job_uuid': 'dataset_job uuid',
                    'started_at': 0,
                    'finished_at': 0,
                    'is_ready': False,
                    'kind': DatasetJobKind.DATA_ALIGNMENT.name,
                    'input_data_batch_num_example': 100,
                    'output_data_batch_num_example': 50,
                    'scheduler_message': '错误信息 ✖️',
                },
                ignore_fields=['updated_at'],
            )

    def test_set_and_get_context(self):
        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            empty_context = job_stage.get_context()
            self.assertEqual(empty_context, DatasetJobStageContext())
            context = DatasetJobStageContext(batch_stats_item_name='batch_stats_item_1',
                                             input_data_batch_num_example=100,
                                             output_data_batch_num_example=50)
            job_stage.set_context(context=context)
            text_context = 'batch_stats_item_name: "batch_stats_item_1"\n' \
                'input_data_batch_num_example: 100\noutput_data_batch_num_example: 50\n'
            self.assertEqual(job_stage.context, text_context)
            target_context = job_stage.get_context()
            self.assertEqual(target_context, context)

    def test_set_scheduler_message(self):
        scheduler_message = '错误信息 ❌'
        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            empty_context = job_stage.get_context()
            self.assertEqual(empty_context, DatasetJobStageContext())
            job_stage.set_scheduler_message(scheduler_message=scheduler_message)
            session.commit()

        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            self.assertEqual(job_stage.get_context().scheduler_message, scheduler_message)

    def test_is_coordinator(self):
        with db.session_scope() as session:
            job_stage: DatasetJobStage = session.query(DatasetJobStage).get(1)
            self.assertTrue(job_stage.is_coordinator())
            job_stage.coordinator_id = 1
            self.assertFalse(job_stage.is_coordinator())


if __name__ == '__main__':
    unittest.main()
