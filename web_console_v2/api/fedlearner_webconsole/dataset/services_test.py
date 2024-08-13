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

import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timedelta, timezone
from google.protobuf.struct_pb2 import Value
from dataset_directory import DatasetDirectory
from pathlib import Path

from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.dataset.meta_data import ImageMetaData, MetaData
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterExpressionKind, SimpleExpression
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition, WorkflowDefinition
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException, ResourceConflictException
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.dataset.models import (DataSourceType, DatasetFormat, DatasetJob, DatasetJobKind,
                                                  DatasetJobStage, DataBatch, DatasetKindV2, DatasetType, Dataset,
                                                  DatasetJobState, DataSource, ImportType, ResourceState, StoreFormat,
                                                  DatasetJobSchedulerState)
from fedlearner_webconsole.dataset.services import (BatchService, DataReader, DataSourceService, DatasetJobService,
                                                    DatasetJobStageService, DatasetService)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.pp_datetime import to_timestamp, now
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupParameter, CleanupPayload
from testing.common import NoWebServerTestCase
from testing.dataset import FakeDatasetJobConfiger
from testing.fake_time_patcher import FakeTimePatcher


class DatasetServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.source_dir = tempfile.mkdtemp()
        self._set_common_dataset()

    def _set_common_dataset(self):
        with db.session_scope() as session:
            dataset = Dataset(
                name='default dataset1',
                uuid='default uuid',
                dataset_type=DatasetType.STREAMING,
                comment='test comment1',
                path=str(self.source_dir),
                project_id=1,
                dataset_kind=DatasetKindV2.RAW,
            )
            session.add(dataset)
            session.commit()

    @patch('envs.Envs.STORAGE_ROOT', '/data')
    def test_create_dataset(self):
        dataset_para = dataset_pb2.DatasetParameter(name='test',
                                                    uuid='fake_uuid',
                                                    type=DatasetType.PSI.value,
                                                    comment='this is a comment',
                                                    project_id=1,
                                                    kind=DatasetKindV2.RAW.value,
                                                    format=DatasetFormat.IMAGE.name,
                                                    is_published=False,
                                                    import_type=ImportType.NO_COPY.value,
                                                    store_format=StoreFormat.CSV.value)

        with db.session_scope() as session:
            with self.assertRaises(NotFoundException):
                DatasetService(session).create_dataset(dataset_parameter=dataset_para)
                session.commit()

        with db.session_scope() as session:
            project = Project()
            session.add(project)
            session.commit()
            dataset_para.project_id = project.id

        with db.session_scope() as session:
            DatasetService(session).create_dataset(dataset_parameter=dataset_para)
            session.commit()

        with db.session_scope() as session:
            dataset = session.query(Dataset).filter(Dataset.name == 'test').one()
            self.assertEqual(dataset.comment, 'this is a comment')
            self.assertEqual(dataset.path, 'file:///data/dataset/fake_uuid_test')
            self.assertEqual(dataset.is_published, False)
            self.assertEqual(dataset.import_type, ImportType.NO_COPY)
            self.assertEqual(dataset.store_format, StoreFormat.CSV)

        dataset_para_published = dataset_pb2.DatasetParameter(name='test_published',
                                                              uuid='fake_uuid_published',
                                                              type=DatasetType.PSI.value,
                                                              comment='this is a comment',
                                                              project_id=1,
                                                              kind=DatasetKindV2.PROCESSED.value,
                                                              format=DatasetFormat.IMAGE.name,
                                                              is_published=True,
                                                              creator_username='fakeuser')

        with db.session_scope() as session:
            DatasetService(session).create_dataset(dataset_parameter=dataset_para_published)
            session.commit()

        with db.session_scope() as session:
            dataset = session.query(Dataset).filter(Dataset.name == 'test_published').one()
            self.assertEqual(dataset.comment, 'this is a comment')
            self.assertEqual(dataset.path, 'file:///data/dataset/fake_uuid_published_test-published')
            self.assertEqual(dataset.is_published, True)
            self.assertEqual(dataset.creator_username, 'fakeuser')

    def test_publish_dataset(self, mock_get_publish_reward: MagicMock):
        with db.session_scope() as session:
            unpublished_dataset = Dataset(id=11,
                                          uuid='123',
                                          name='none_published_dataset',
                                          dataset_type=DatasetType.STREAMING,
                                          comment='test comment',
                                          path='/data/dataset/123',
                                          is_published=False,
                                          project_id=1,
                                          dataset_format=DatasetFormat.TABULAR.value)
            no_uuid_dataset = Dataset(id=12,
                                      name='none_published_dataset',
                                      dataset_type=DatasetType.STREAMING,
                                      comment='test comment',
                                      path='/data/dataset/123',
                                      is_published=False,
                                      project_id=1,
                                      dataset_format=DatasetFormat.TABULAR.value)
            session.add(unpublished_dataset)
            session.add(no_uuid_dataset)
            session.commit()
        # test unpublish to publish
        with db.session_scope() as session:
            dataset = DatasetService(session=session).publish_dataset(dataset_id=11, value=100)
            session.commit()
        mock_get_publish_reward.assert_called_once_with(dataset_uuid='123')
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(11)
            self.assertTrue(dataset.is_published)
            self.assertEqual(dataset.get_meta_info().value, 100)
            self.assertIsNotNone(dataset.ticket_uuid)
            self.assertEqual(dataset.ticket_status, TicketStatus.APPROVED)
        # test publish to publish
        with db.session_scope() as session:
            dataset = DatasetService(session=session).publish_dataset(dataset_id=11)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(11)
            self.assertTrue(dataset.is_published)
            self.assertIsNotNone(dataset.ticket_uuid)
        # test unknown dataset
        with db.session_scope() as session:
            with self.assertRaises(NotFoundException):
                DatasetService(session=session).publish_dataset(dataset_id=100)
        # test no uuid dataset
        with db.session_scope() as session:
            dataset = DatasetService(session=session).publish_dataset(dataset_id=12)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(12)
            self.assertIsNotNone(dataset.uuid)
            self.assertIsNotNone(dataset.ticket_uuid)
            self.assertEqual(dataset.ticket_status, TicketStatus.APPROVED)

    def test_withdraw_dataset(self):
        with db.session_scope() as session:
            published_dataset = Dataset(id=10,
                                        uuid='123',
                                        name='published_dataset',
                                        dataset_type=DatasetType.STREAMING,
                                        comment='test comment',
                                        path='/data/dataset/123',
                                        is_published=True,
                                        project_id=1,
                                        dataset_format=DatasetFormat.TABULAR.value,
                                        ticket_uuid='ticket_uuid',
                                        ticket_status=TicketStatus.APPROVED)
            session.add(published_dataset)
            session.commit()
        # test publish to unpublish
        with db.session_scope() as session:
            DatasetService(session=session).withdraw_dataset(dataset_id=10)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertFalse(dataset.is_published)
            self.assertIsNone(dataset.ticket_uuid)
            self.assertIsNone(dataset.ticket_status)
        # test unpublish to unpublish
        with db.session_scope() as session:
            DatasetService(session=session).withdraw_dataset(dataset_id=10)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertFalse(dataset.is_published)
        # test unknown dataset
        with db.session_scope() as session:
            with self.assertRaises(NotFoundException):
                DatasetService(session=session).publish_dataset(dataset_id=100)

    def test_get_published_datasets(self):
        update_time = datetime(2012, 1, 14, 12, 0, 5)
        with db.session_scope() as session:
            dataset1 = Dataset(
                id=10,
                uuid='1',
                name='dataset_1',
                dataset_type=DatasetType.PSI,
                project_id=1,
                path='/data/dataset_1/',
                is_published=True,
                dataset_format=DatasetFormat.TABULAR.value,
                updated_at=update_time,
                dataset_kind=DatasetKindV2.RAW,
            )
            dataset_job1 = DatasetJob(id=10,
                                      uuid=resource_uuid(),
                                      input_dataset_id=0,
                                      output_dataset_id=dataset1.id,
                                      kind=DatasetJobKind.IMPORT_SOURCE,
                                      project_id=1,
                                      state=DatasetJobState.SUCCEEDED,
                                      deleted_at=datetime(2022, 1, 1))
            session.add_all([dataset1, dataset_job1])
            dataset2 = Dataset(
                id=11,
                uuid='2',
                name='dataset_2',
                dataset_type=DatasetType.PSI,
                project_id=1,
                path='/data/dataset_2/',
                is_published=True,
                dataset_format=DatasetFormat.TABULAR.value,
                updated_at=update_time,
                dataset_kind=DatasetKindV2.PROCESSED,
            )
            dataset_job2 = DatasetJob(id=11,
                                      uuid=resource_uuid(),
                                      input_dataset_id=0,
                                      output_dataset_id=dataset2.id,
                                      kind=DatasetJobKind.IMPORT_SOURCE,
                                      project_id=1,
                                      state=DatasetJobState.SUCCEEDED,
                                      time_range=timedelta(days=1))
            session.add_all([dataset2, dataset_job2])
            data_source = DataSource(
                id=12,
                uuid='3',
                name='dataset_3',
                dataset_type=DatasetType.PSI,
                project_id=1,
                path='/data/dataset_2/',
                is_published=True,
                dataset_format=DatasetFormat.TABULAR.value,
                updated_at=update_time,
            )
            session.add(data_source)
            dataset4 = Dataset(
                id=13,
                uuid='4',
                name='dataset_4',
                dataset_type=DatasetType.PSI,
                project_id=1,
                path='/data/dataset_4/',
                is_published=True,
                dataset_format=DatasetFormat.TABULAR.value,
                updated_at=update_time,
            )
            dataset_job4 = DatasetJob(id=13,
                                      uuid=resource_uuid(),
                                      input_dataset_id=0,
                                      output_dataset_id=dataset4.id,
                                      kind=DatasetJobKind.IMPORT_SOURCE,
                                      project_id=1,
                                      state=DatasetJobState.STOPPED)
            session.add_all([dataset4, dataset_job4])
            session.commit()
        dataref_1 = dataset_pb2.ParticipantDatasetRef(uuid='1',
                                                      name='dataset_1',
                                                      format=DatasetFormat.TABULAR.name,
                                                      file_size=0,
                                                      updated_at=to_timestamp(update_time),
                                                      dataset_kind=DatasetKindV2.RAW.name,
                                                      dataset_type=DatasetType.PSI.name,
                                                      auth_status='PENDING')
        dataref_2 = dataset_pb2.ParticipantDatasetRef(uuid='2',
                                                      name='dataset_2',
                                                      format=DatasetFormat.TABULAR.name,
                                                      file_size=0,
                                                      updated_at=to_timestamp(update_time),
                                                      dataset_kind=DatasetKindV2.PROCESSED.name,
                                                      dataset_type=DatasetType.PSI.name,
                                                      auth_status='PENDING')
        with db.session_scope() as session:
            dataset_service = DatasetService(session=session)
            self.assertEqual(dataset_service.get_published_datasets(project_id=1, state=ResourceState.SUCCEEDED),
                             [dataref_2, dataref_1])
            self.assertEqual(
                dataset_service.get_published_datasets(project_id=1,
                                                       kind=DatasetKindV2.RAW,
                                                       state=ResourceState.SUCCEEDED), [dataref_1])
            self.assertEqual(dataset_service.get_published_datasets(project_id=1, uuid='2'), [dataref_2])
            filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                          simple_exp=SimpleExpression(field='uuid', string_value='2'))
            self.assertEqual(dataset_service.get_published_datasets(project_id=1, filter_exp=filter_exp), [dataref_2])
            self.assertEqual(
                dataset_service.get_published_datasets(project_id=1,
                                                       state=ResourceState.SUCCEEDED,
                                                       time_range=timedelta(days=1)), [dataref_2])

    @patch('fedlearner_webconsole.cleanup.services.CleanupService.create_cleanup')
    def test_cleanup_dataset(self, cleanup_mock: MagicMock):
        # create a test dateset
        with db.session_scope() as session:
            published_dataset = Dataset(id=333,
                                        uuid='123',
                                        name='published_dataset',
                                        dataset_type=DatasetType.STREAMING,
                                        comment='test comment',
                                        path='/data/dataset/123',
                                        is_published=True,
                                        project_id=1,
                                        dataset_format=DatasetFormat.TABULAR.value)
            session.add(published_dataset)
            session.commit()
        # test cleanup failed case
        cleanup_mock.reset_mock()
        cleanup_mock.side_effect = Exception('fake-exception')
        with db.session_scope() as session:
            dataset = session.query(Dataset).with_for_update().populate_existing().get(333)
            service = DatasetService(session)
            self.assertRaises(Exception, service.cleanup_dataset, dataset)
        # test cleanup dataset success
        cleanup_mock.side_effect = None
        cleanup_mock.return_value = None
        fake_time = datetime(2022, 4, 14, 0, 0, 0, 0, tzinfo=timezone.utc)
        time_patcher = FakeTimePatcher()
        time_patcher.start(fake_time)
        with db.session_scope() as session:
            dataset = session.query(Dataset).with_for_update().populate_existing().get(333)
            service = DatasetService(session)
            service.cleanup_dataset(dataset)
            session.commit()
        expected_target_start_at = to_timestamp(fake_time + DatasetService.DATASET_CLEANUP_DEFAULT_DELAY)
        expected_payload = CleanupPayload(paths=['/data/dataset/123'])
        expected_cleanup_param = CleanupParameter(resource_id=333,
                                                  resource_type='DATASET',
                                                  target_start_at=expected_target_start_at,
                                                  payload=expected_payload)
        cleanup_mock.assert_called_with(cleanup_parmeter=expected_cleanup_param)
        with db.session_scope() as session:
            self.assertRaises(NotFoundException, service.get_dataset, 333)
        time_patcher.stop()

    def test_query_dataset_with_parent_job(self):
        with db.session_scope() as session:
            query = DatasetService(session).query_dataset_with_parent_job()
            statement = self.generate_mysql_statement(query)
            expected_statement = 'FROM datasets_v2 LEFT OUTER JOIN dataset_jobs_v2 ' \
                'ON dataset_jobs_v2.output_dataset_id = datasets_v2.id ' \
                'AND dataset_jobs_v2.input_dataset_id != datasets_v2.id'
            self.assertTrue(expected_statement in statement)

    @patch('fedlearner_webconsole.dataset.services.DataReader.metadata')
    @patch('fedlearner_webconsole.dataset.services.DataReader.image_metadata')
    def test_get_dataset_preview(self, mock_image_metadata: MagicMock, mock_metadata: MagicMock):
        mock_metadata.return_value = MetaData()
        mock_image_metadata.return_value = ImageMetaData(
            thumbnail_dir_path='/data/dataset/123/meta/20220101/thumbnails')
        with db.session_scope() as session:
            dataset = Dataset(id=10,
                              uuid='dataset uuid',
                              name='dataset',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment',
                              path='/data/dataset/123',
                              is_published=True,
                              project_id=1,
                              dataset_format=DatasetFormat.TABULAR.value)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220101',
                                   path='/data/dataset/123/batch/20220101',
                                   dataset_id=10,
                                   event_time=datetime(year=2022, month=1, day=1))
            session.add(data_batch)
            session.commit()
        with db.session_scope() as session:
            dataset_service = DatasetService(session=session)
            dataset_service.get_dataset_preview(dataset_id=10, batch_id=1)
            mock_metadata.assert_called_once_with(batch_name='20220101')
            dataset = session.query(Dataset).get(10)
            dataset.dataset_format = DatasetFormat.IMAGE.value
            session.flush()
            dataset_service.get_dataset_preview(dataset_id=10, batch_id=1)
            mock_image_metadata.assert_called_once_with(batch_name='20220101',
                                                        thumbnail_dir_path='/data/dataset/123/meta/20220101/thumbnails')

    @patch('fedlearner_webconsole.dataset.services.DataReader.metadata')
    def test_feature_metrics(self, mock_metadata: MagicMock):
        mock_metadata.return_value = MetaData()
        with db.session_scope() as session:
            dataset = Dataset(id=10,
                              uuid='dataset uuid',
                              name='dataset',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment',
                              path='/data/dataset/123',
                              is_published=True,
                              project_id=1,
                              dataset_format=DatasetFormat.TABULAR.value)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220101',
                                   path='/data/dataset/123/batch/20220101',
                                   dataset_id=10,
                                   event_time=datetime(year=2022, month=1, day=1))
            session.add(data_batch)
            session.commit()
        with db.session_scope() as session:
            dataset_service = DatasetService(session=session)
            val = dataset_service.feature_metrics(name='raw_id', dataset_id=10, data_batch_id=1)
            expected_val = {
                'name': 'raw_id',
                'metrics': {},
                'hist': {},
            }
            self.assertEqual(val, expected_val)
            mock_metadata.assert_called_once_with(batch_name='20220101')

    def test_get_data_batch(self):
        with db.session_scope() as session:
            dataset = Dataset(id=10,
                              uuid='dataset uuid',
                              name='dataset',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment',
                              path='/data/dataset/123',
                              is_published=True,
                              project_id=1,
                              dataset_format=DatasetFormat.TABULAR.value)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220101',
                                   path='/data/dataset/123/batch/20220101',
                                   dataset_id=10,
                                   event_time=datetime(year=2022, month=1, day=1))
            session.add(data_batch)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            dataset_service = DatasetService(session=session)
            data_batch = dataset_service.get_data_batch(dataset=dataset, event_time=datetime(2022, 1, 1))
            self.assertEqual(data_batch.id, 1)
            data_batch = dataset_service.get_data_batch(dataset=dataset, event_time=datetime(2022, 1, 2))
            self.assertIsNone(data_batch)
            dataset.dataset_type = DatasetType.PSI
            data_batch = dataset_service.get_data_batch(dataset=dataset)
            self.assertEqual(data_batch.id, 1)


class DataSourceServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.source_dir = tempfile.mkdtemp()
        self._set_default_project()
        self._set_common_dataset()

    def _set_default_project(self):
        with db.session_scope() as session:
            project = Project(id=1, name='default_project')
            session.add(project)
            session.commit()

    def _set_common_dataset(self):
        with db.session_scope() as session:
            dataset = Dataset(
                name='default dataset1',
                dataset_type=DatasetType.STREAMING,
                comment='test comment1',
                path=str(self.source_dir),
                project_id=1,
            )
            session.add(dataset)
            session.commit()

    @patch('fedlearner_webconsole.dataset.services.get_current_user', lambda: User(id=1, username='xiaohang'))
    def test_create_data_source(self):
        data_source_parameter = dataset_pb2.DataSource(name='default data_source',
                                                       url='hdfs:///fack_url',
                                                       project_id=1,
                                                       type=DataSourceType.HDFS.value,
                                                       is_user_upload=False,
                                                       dataset_format=DatasetFormat.TABULAR.name,
                                                       store_format=StoreFormat.CSV.value,
                                                       dataset_type=DatasetType.PSI.value)
        with db.session_scope() as session:
            data_source = DataSourceService(session=session).create_data_source(
                data_source_parameter=data_source_parameter)
            session.commit()
        with db.session_scope() as session:
            data_source = session.query(DataSource).filter_by(name='default data_source').first()
            self.assertEqual(data_source.name, data_source_parameter.name)
            self.assertEqual(data_source.path, data_source_parameter.url)
            self.assertEqual(data_source.project_id, data_source_parameter.project_id)
            self.assertEqual(data_source.creator_username, 'xiaohang')
            self.assertEqual(data_source.get_meta_info().datasource_type, data_source_parameter.type)
            self.assertEqual(data_source.get_meta_info().is_user_upload, data_source_parameter.is_user_upload)
            self.assertEqual(data_source.dataset_format, DatasetFormat.TABULAR.value)
            self.assertEqual(data_source.store_format, StoreFormat.CSV)
            self.assertEqual(data_source.dataset_type, DatasetType.PSI)
            self.assertIsNotNone(data_source.id)
            self.assertIsNotNone(data_source.created_at)

    def test_get_data_sources(self):
        with db.session_scope() as session:
            datasource_1 = DataSource(id=100,
                                      uuid='data_source_1_uuid',
                                      name='datasource_1',
                                      path='hdfs:///data/fake_path_1',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 5),
                                      is_published=False,
                                      store_format=StoreFormat.TFRECORDS,
                                      dataset_format=DatasetFormat.IMAGE.value,
                                      dataset_type=DatasetType.STREAMING)
            datasource_1.set_meta_info(meta=dataset_pb2.DatasetMetaInfo(
                datasource_type=DataSourceType.HDFS.value, is_user_upload=False, is_user_export=False))
            datasource_2 = DataSource(id=101,
                                      uuid='data_source_2_uuid',
                                      name='datasource_2',
                                      path='file:///data/fake_path_2',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 6),
                                      is_published=False,
                                      store_format=StoreFormat.CSV,
                                      dataset_format=DatasetFormat.TABULAR.value,
                                      dataset_type=DatasetType.PSI)
            datasource_2.set_meta_info(meta=dataset_pb2.DatasetMetaInfo(
                datasource_type=DataSourceType.FILE.value, is_user_upload=False, is_user_export=False))
            datasource_3 = DataSource(id=102,
                                      uuid='data_source_3_uuid',
                                      name='datasource_3',
                                      path='/upload/fake_path_3',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 7),
                                      is_published=False)
            datasource_3.set_meta_info(meta=dataset_pb2.DatasetMetaInfo(
                datasource_type=DataSourceType.FILE.value, is_user_upload=True, is_user_export=False))
            datasource_4 = DataSource(id=103,
                                      uuid='data_source_4_uuid',
                                      name='datasource_4',
                                      path='/upload/fake_path_4',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 8),
                                      is_published=False)
            datasource_4.set_meta_info(meta=dataset_pb2.DatasetMetaInfo(
                datasource_type=DataSourceType.FILE.value, is_user_upload=True, is_user_export=True))
            session.add(datasource_1)
            session.add(datasource_2)
            session.add(datasource_3)
            session.add(datasource_4)
            session.commit()
        with db.session_scope() as session:
            expected_datasources = [
                dataset_pb2.DataSource(id=101,
                                       uuid='data_source_2_uuid',
                                       name='datasource_2',
                                       url='file:///data/fake_path_2',
                                       project_id=1,
                                       created_at=to_timestamp(datetime(2012, 1, 14, 12, 0, 6)),
                                       type=DataSourceType.FILE.value,
                                       is_user_upload=False,
                                       dataset_format='TABULAR',
                                       store_format='CSV',
                                       dataset_type='PSI'),
                dataset_pb2.DataSource(id=100,
                                       uuid='data_source_1_uuid',
                                       name='datasource_1',
                                       url='hdfs:///data/fake_path_1',
                                       project_id=1,
                                       created_at=to_timestamp(datetime(2012, 1, 14, 12, 0, 5)),
                                       type=DataSourceType.HDFS.value,
                                       is_user_upload=False,
                                       dataset_format='IMAGE',
                                       store_format='TFRECORDS',
                                       dataset_type='STREAMING')
            ]
            data_sources = DataSourceService(session=session).get_data_sources(project_id=1)
            self.assertEqual(data_sources, expected_datasources)

    def test_delete_data_source(self):
        with db.session_scope() as session:
            datasource = DataSource(id=100,
                                    uuid=resource_uuid(),
                                    name='datasource',
                                    path='hdfs:///data/fake_path',
                                    project_id=1,
                                    created_at=datetime(2012, 1, 14, 12, 0, 5),
                                    is_published=False)
            session.add(datasource)
            session.commit()
        with db.session_scope() as session:
            DataSourceService(session=session).delete_data_source(data_source_id=100)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(DataSource).execution_options(include_deleted=True).get(100)
            self.assertIsNotNone(dataset.deleted_at)
            with self.assertRaises(NotFoundException):
                DataSourceService(session=session).delete_data_source(data_source_id=102)

        with db.session_scope() as session:
            datasource = DataSource(id=101,
                                    uuid=resource_uuid(),
                                    name='datasource',
                                    path='hdfs:///data/fake_path',
                                    project_id=1,
                                    created_at=datetime(2012, 1, 14, 12, 0, 5),
                                    is_published=False)
            session.add(datasource)
            dataset_job = DatasetJob(id=10,
                                     uuid='test-uuid',
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     project_id=1,
                                     workflow_id=1,
                                     input_dataset_id=datasource.id,
                                     output_dataset_id=2,
                                     coordinator_id=1,
                                     state=DatasetJobState.RUNNING)
            session.add(dataset_job)
            session.commit()
        with db.session_scope() as session:
            with self.assertRaises(ResourceConflictException):
                DataSourceService(session=session).delete_data_source(data_source_id=101)
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(10)
            dataset_job.state = DatasetJobState.SUCCEEDED
            session.commit()
        with db.session_scope() as session:
            DataSourceService(session=session).delete_data_source(data_source_id=101)
            session.commit()
        with db.session_scope() as session:
            dataset = session.query(DataSource).execution_options(include_deleted=True).get(101)
            self.assertIsNotNone(dataset.deleted_at)


class BatchServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test-project')
            session.add(project)
            session.commit()

    def test_create_orphan_batch(self):
        batch_para = dataset_pb2.BatchParameter(comment='this is a comment for batch',
                                                path='/data/dataset/test/batch/batch_1')

        with db.session_scope() as session:
            with self.assertRaises(NotFoundException):
                BatchService(session).create_batch(batch_parameter=batch_para)
                session.commit()

    @patch('envs.Envs.STORAGE_ROOT', '/data')
    def test_create_psi_batch(self):
        batch_para = dataset_pb2.BatchParameter()
        with db.session_scope() as session:
            dataset_para = dataset_pb2.DatasetParameter(name='test',
                                                        uuid='fake_uuid',
                                                        type=DatasetType.PSI.value,
                                                        comment='this is a comment',
                                                        project_id=1,
                                                        path='/data/dataset/test/',
                                                        kind=DatasetKindV2.EXPORTED.value,
                                                        format=DatasetFormat.IMAGE.name)
            dataset = DatasetService(session).create_dataset(dataset_parameter=dataset_para)
            session.commit()
            batch_para.dataset_id = dataset.id

        with db.session_scope() as session:
            batch = BatchService(session).create_batch(batch_parameter=batch_para)
            session.commit()
            self.assertEqual(batch.dataset_id, batch_para.dataset_id)
            self.assertIsNone(batch.event_time)
            self.assertEqual(batch.path, '/data/dataset/test/batch/0')
            self.assertEqual(batch.name, '0')

        with db.session_scope() as session:
            with self.assertRaises(InvalidArgumentException):
                batch = BatchService(session).create_batch(batch_parameter=batch_para)
                session.commit()

    @patch('envs.Envs.STORAGE_ROOT', '/data')
    def test_create_streaming_batch(self):
        batch_para = dataset_pb2.BatchParameter()
        with db.session_scope() as session:
            dataset_para = dataset_pb2.DatasetParameter(name='test',
                                                        uuid='fake_uuid',
                                                        type=DatasetType.STREAMING.value,
                                                        comment='this is a comment',
                                                        project_id=1,
                                                        kind=DatasetKindV2.RAW.value,
                                                        format=DatasetFormat.IMAGE.name)
            dataset = DatasetService(session).create_dataset(dataset_parameter=dataset_para)
            session.commit()
            batch_para.dataset_id = dataset.id

        with db.session_scope() as session:
            with self.assertRaises(InvalidArgumentException):
                batch_para.event_time = 0
                batch = BatchService(session).create_batch(batch_parameter=batch_para)
                session.commit()

        with db.session_scope() as session:
            event_time = now()
            batch_para.event_time = to_timestamp(event_time)
            batch = BatchService(session).create_batch(batch_parameter=batch_para)
            session.flush()
            self.assertEqual(batch.dataset_id, batch_para.dataset_id)
            self.assertEqual(batch.event_time, event_time.replace(microsecond=0))
            self.assertEqual(batch.path, f'file:///data/dataset/fake_uuid_test/batch/{event_time.strftime("%Y%m%d")}')
            self.assertEqual(batch.name, event_time.strftime('%Y%m%d'))

        with db.session_scope() as session:
            event_time = now()
            batch_para.event_time = to_timestamp(event_time)
            batch_para.cron_type = dataset_pb2.CronType.HOURLY
            batch = BatchService(session).create_batch(batch_parameter=batch_para)
            session.flush()
            self.assertEqual(batch.dataset_id, batch_para.dataset_id)
            self.assertEqual(batch.event_time, event_time.replace(microsecond=0))
            self.assertEqual(batch.path,
                             f'file:///data/dataset/fake_uuid_test/batch/{event_time.strftime("%Y%m%d-%H")}')
            self.assertEqual(batch.name, event_time.strftime('%Y%m%d-%H'))

    def test_get_next_batch(self):
        with db.session_scope() as session:
            dataset = Dataset(id=1,
                              name='output dataset',
                              uuid=resource_uuid(),
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment2',
                              path='/data/dataset/123',
                              project_id=1)
            session.add(dataset)

            data_batch = DataBatch(id=1,
                                   name='20220101-08',
                                   dataset_id=1,
                                   event_time=datetime(year=2000, month=1, day=1, hour=8),
                                   latest_parent_dataset_job_stage_id=1)
            session.add(data_batch)
            session.commit()

        # test no stage
        with db.session_scope() as session:
            data_batch = session.query(DataBatch).get(1)
            self.assertIsNone(BatchService(session).get_next_batch(data_batch=data_batch), None)

        # test no dataset_job
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStage(name='20220101-stage0',
                                                dataset_job_id=1,
                                                data_batch_id=1,
                                                project_id=1,
                                                event_time=datetime(year=2000, month=1, day=1),
                                                uuid=resource_uuid())
            session.add(dataset_job_stage)
            session.commit()
        with db.session_scope() as session:
            data_batch = session.query(DataBatch).get(1)
            self.assertIsNone(BatchService(session).get_next_batch(data_batch=data_batch), None)

        # test no next batch
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='test-uuid',
                                     kind=DatasetJobKind.IMPORT_SOURCE,
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=1,
                                     workflow_id=0,
                                     input_dataset_id=0,
                                     output_dataset_id=1,
                                     coordinator_id=0,
                                     time_range=timedelta(hours=1))
            session.add(dataset_job)
            session.commit()
        with db.session_scope() as session:
            data_batch = session.query(DataBatch).get(1)
            self.assertIsNone(BatchService(session).get_next_batch(data_batch=data_batch), None)

        # test get next batch
        with db.session_scope() as session:
            data_batch = DataBatch(id=2,
                                   name='20220102',
                                   dataset_id=1,
                                   event_time=datetime(year=2000, month=1, day=1, hour=9))
            session.add(data_batch)
            session.commit()
        with db.session_scope() as session:
            data_batch = session.query(DataBatch).get(1)
            next_data_batch = session.query(DataBatch).get(2)
            self.assertEqual(BatchService(session).get_next_batch(data_batch=data_batch), next_data_batch)


class DatasetJobServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test-project')
            session.add(project)
            session.flush([project])

            input_dataset = DataSource(name='input dataset',
                                       uuid=resource_uuid(),
                                       dataset_type=DatasetType.STREAMING,
                                       comment='test comment1',
                                       path='/data/dataset/123',
                                       project_id=project.id)
            session.add(input_dataset)

            output_dataset = Dataset(name='output dataset',
                                     uuid=resource_uuid(),
                                     dataset_type=DatasetType.STREAMING,
                                     comment='test comment1',
                                     path='/data/dataset/123',
                                     project_id=project.id)
            session.add(output_dataset)

            session.commit()
            self.project_id = project.id
            self.input_dataset_id = input_dataset.id
            self.output_dataset_id = output_dataset.id

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.services.DatasetJobConfiger.from_kind',
           lambda *args: FakeDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.dataset.services.get_current_user', lambda: User(id=1, username='test user'))
    @patch('fedlearner_webconsole.dataset.services.emit_dataset_job_submission_store')
    def test_create_dataset_job_as_coordinator(self, mock_emit_dataset_job_submission_store: MagicMock):
        with db.session_scope() as session:
            input_dataset = session.query(DataSource).get(self.input_dataset_id)
            global_configs = dataset_pb2.DatasetJobGlobalConfigs()
            global_configs.global_configs['test_domain'].MergeFrom(
                dataset_pb2.DatasetJobConfig(dataset_uuid=input_dataset.uuid,
                                             variables=[
                                                 Variable(name='hello',
                                                          value_type=Variable.ValueType.NUMBER,
                                                          typed_value=Value(number_value=1)),
                                                 Variable(name='test',
                                                          value_type=Variable.ValueType.STRING,
                                                          typed_value=Value(string_value='test_value')),
                                             ]))
            dataset_job = DatasetJobService(session).create_as_coordinator(project_id=self.project_id,
                                                                           kind=DatasetJobKind.IMPORT_SOURCE,
                                                                           output_dataset_id=self.output_dataset_id,
                                                                           global_configs=global_configs,
                                                                           time_range=timedelta(days=1))
            session.commit()
            self.assertEqual(len(dataset_job.get_global_configs().global_configs['test_domain'].variables), 2)
            self.assertEqual(dataset_job.name, 'output dataset')
            self.assertTrue(dataset_job.get_context().has_stages)
            self.assertEqual(dataset_job.time_range, timedelta(days=1))
            self.assertEqual(dataset_job.creator_username, 'test user')
            mock_emit_dataset_job_submission_store.assert_called_once_with(uuid=ANY,
                                                                           kind=DatasetJobKind.IMPORT_SOURCE,
                                                                           coordinator_id=0)

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(name='hahaha', domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.services.emit_dataset_job_submission_store')
    def test_create_dataset_job_as_participant(self, mock_emit_dataset_job_submission_store: MagicMock):
        with db.session_scope() as session:
            input_dataset = session.query(Dataset).get(self.input_dataset_id)
            global_configs = dataset_pb2.DatasetJobGlobalConfigs()
            global_configs.global_configs['test_domain'].MergeFrom(
                dataset_pb2.DatasetJobConfig(dataset_uuid=input_dataset.uuid,
                                             variables=[
                                                 Variable(name='hello',
                                                          value_type=Variable.ValueType.NUMBER,
                                                          typed_value=Value(number_value=1)),
                                                 Variable(name='test',
                                                          value_type=Variable.ValueType.STRING,
                                                          typed_value=Value(string_value='test_value')),
                                             ]))
            config = WorkflowDefinition(variables=[
                Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))
            ],
                                        job_definitions=[
                                            JobDefinition(variables=[
                                                Variable(name='hello_from_job',
                                                         value_type=Variable.ValueType.NUMBER,
                                                         typed_value=Value(number_value=3))
                                            ])
                                        ])

            dataset_job = DatasetJobService(session).create_as_participant(project_id=self.project_id,
                                                                           kind=DatasetJobKind.IMPORT_SOURCE,
                                                                           config=config,
                                                                           output_dataset_id=self.output_dataset_id,
                                                                           coordinator_id=1,
                                                                           uuid='u12345',
                                                                           global_configs=global_configs,
                                                                           creator_username='test user')
            session.commit()
            self.assertTrue(dataset_job.get_context().has_stages)
            mock_emit_dataset_job_submission_store.assert_called_once_with(uuid='u12345',
                                                                           kind=DatasetJobKind.IMPORT_SOURCE,
                                                                           coordinator_id=1)

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).filter(DatasetJob.uuid == 'u12345').first()
            self.assertIsNone(dataset_job.global_configs)
            self.assertEqual(dataset_job.output_dataset_id, self.output_dataset_id)
            self.assertEqual(dataset_job.kind, DatasetJobKind.IMPORT_SOURCE)
            self.assertEqual(dataset_job.project_id, self.project_id)
            self.assertEqual(dataset_job.coordinator_id, 1)
            self.assertEqual(dataset_job.name, 'output dataset')
            self.assertEqual(dataset_job.creator_username, 'test user')
            self.assertIsNone(dataset_job.time_range)

        # test with time_range
        mock_emit_dataset_job_submission_store.reset_mock()
        with db.session_scope() as session:
            dataset_job = DatasetJobService(session).create_as_participant(project_id=self.project_id,
                                                                           kind=DatasetJobKind.IMPORT_SOURCE,
                                                                           config=config,
                                                                           output_dataset_id=self.output_dataset_id,
                                                                           coordinator_id=1,
                                                                           uuid='u12345 with time_range',
                                                                           global_configs=global_configs,
                                                                           creator_username='test user',
                                                                           time_range=timedelta(days=1))
            session.commit()
            self.assertTrue(dataset_job.get_context().has_stages)
            mock_emit_dataset_job_submission_store.assert_called_once_with(uuid='u12345 with time_range',
                                                                           kind=DatasetJobKind.IMPORT_SOURCE,
                                                                           coordinator_id=1)

        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).filter(DatasetJob.uuid == 'u12345 with time_range').first()
            self.assertEqual(dataset_job.time_range, timedelta(days=1))

    def test_is_local(self):
        with db.session_scope() as session:
            service = DatasetJobService(session=session)
            self.assertTrue(service.is_local(dataset_job_kind=DatasetJobKind.IMPORT_SOURCE))
            self.assertFalse(service.is_local(dataset_job_kind=DatasetJobKind.DATA_ALIGNMENT))

    def test_need_distribute(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='test-uuid',
                                     kind=DatasetJobKind.EXPORT,
                                     project_id=1,
                                     workflow_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     coordinator_id=1)
            service = DatasetJobService(session=session)
            self.assertTrue(service.need_distribute(dataset_job=dataset_job))
            dataset_job.coordinator_id = 0
            self.assertFalse(service.need_distribute(dataset_job=dataset_job))
            dataset_job.kind = DatasetJobKind.OT_PSI_DATA_JOIN
            self.assertTrue(service.need_distribute(dataset_job=dataset_job))

    @patch('fedlearner_webconsole.dataset.services.DatasetJobService.need_distribute')
    @patch('fedlearner_webconsole.dataset.services.ParticipantService.get_platform_participants_by_project')
    def test_get_participants_need_distribute(self, mock_get_platform_participants_by_project: MagicMock,
                                              mock_need_distribute: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='test-uuid',
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     project_id=1,
                                     workflow_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     coordinator_id=1)
            service = DatasetJobService(session=session)

            # test no need to distribute
            mock_need_distribute.return_value = False
            self.assertEqual(service.get_participants_need_distribute(dataset_job), [])

            # test no plateform participant
            mock_need_distribute.return_value = True
            mock_get_platform_participants_by_project.return_value = []
            self.assertEqual(service.get_participants_need_distribute(dataset_job), [])

            # test get platform participants
            mock_need_distribute.return_value = True
            mock_get_platform_participants_by_project.return_value = ['participants1', 'participants2']
            self.assertEqual(service.get_participants_need_distribute(dataset_job), ['participants1', 'participants2'])

    @patch('fedlearner_webconsole.dataset.services.now', lambda: datetime(2022, 1, 1, 12, 0, 0))
    def test_start(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     coordinator_id=2,
                                     uuid='uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.PENDING)
            DatasetJobService(session).start_dataset_job(dataset_job)
            session.add(dataset_job)
            session.commit()
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.state, DatasetJobState.RUNNING)
            self.assertEqual(dataset_job.started_at, datetime(2022, 1, 1, 12, 0, 0))

    @patch('fedlearner_webconsole.dataset.services.now', lambda: datetime(2022, 1, 1, 12, 0, 0))
    @patch('fedlearner_webconsole.dataset.services.emit_dataset_job_duration_store')
    def test_finish(self, mock_emit_dataset_job_duration_store: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     coordinator_id=2,
                                     uuid='uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.PENDING,
                                     created_at=datetime(2022, 1, 1, 11, 0, 0))
            dataset_job_service = DatasetJobService(session)
            with self.assertRaises(ValueError):
                dataset_job_service.finish_dataset_job(dataset_job=dataset_job, finish_state=DatasetJobState.RUNNING)
                self.assertEqual(dataset_job.state, DatasetJobState.PENDING)
                self.assertIsNone(dataset_job.finished_at)
                mock_emit_dataset_job_duration_store.assert_not_called()
            dataset_job_service.finish_dataset_job(dataset_job=dataset_job, finish_state=DatasetJobState.SUCCEEDED)
            mock_emit_dataset_job_duration_store.assert_called_once_with(duration=3600,
                                                                         uuid='uuid',
                                                                         kind=DatasetJobKind.DATA_ALIGNMENT,
                                                                         coordinator_id=2,
                                                                         state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            session.commit()
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.state, DatasetJobState.SUCCEEDED)
            self.assertEqual(dataset_job.finished_at, datetime(2022, 1, 1, 12, 0, 0))

    def test_start_cron_scheduler(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     coordinator_id=2,
                                     uuid='uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING,
                                     created_at=datetime(2022, 1, 1, 11, 0, 0),
                                     scheduler_state=DatasetJobSchedulerState.STOPPED)
            DatasetJobService(session=session).start_cron_scheduler(dataset_job=dataset_job)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.STOPPED)
            dataset_job.time_range = timedelta(days=1)
            DatasetJobService(session=session).start_cron_scheduler(dataset_job=dataset_job)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.RUNNABLE)

    def test_stop_cron_scheduler(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     coordinator_id=2,
                                     uuid='uuid',
                                     project_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN,
                                     state=DatasetJobState.PENDING,
                                     created_at=datetime(2022, 1, 1, 11, 0, 0),
                                     scheduler_state=DatasetJobSchedulerState.RUNNABLE)
            DatasetJobService(session=session).stop_cron_scheduler(dataset_job=dataset_job)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.RUNNABLE)
            dataset_job.time_range = timedelta(days=1)
            DatasetJobService(session=session).stop_cron_scheduler(dataset_job=dataset_job)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.STOPPED)

    def test_delete_dataset_job(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='test-uuid',
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.PENDING,
                                     project_id=1,
                                     workflow_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     coordinator_id=1)

            # test dataset_job is not finished:
            with self.assertRaises(ResourceConflictException):
                DatasetJobService(session).delete_dataset_job(dataset_job=dataset_job)
            self.assertIsNone(dataset_job.deleted_at)

            # test stop dataset_job successfully
            dataset_job.state = DatasetJobState.SUCCEEDED
            DatasetJobService(session).delete_dataset_job(dataset_job=dataset_job)
            self.assertIsNotNone(dataset_job.deleted_at)


class DatasetJobStageServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test-project')
            session.add(project)
            session.flush([project])

            input_dataset = DataSource(name='input dataset',
                                       uuid=resource_uuid(),
                                       dataset_type=DatasetType.STREAMING,
                                       comment='test comment1',
                                       path='/data/data_source/123',
                                       project_id=project.id)
            session.add(input_dataset)

            output_dataset = Dataset(name='output dataset',
                                     uuid=resource_uuid(),
                                     dataset_type=DatasetType.STREAMING,
                                     comment='test comment2',
                                     path='/data/dataset/123',
                                     project_id=project.id)
            session.add(output_dataset)
            session.flush()

            dataset_job = DatasetJob(uuid='test-uuid',
                                     kind=DatasetJobKind.IMPORT_SOURCE,
                                     state=DatasetJobState.SUCCEEDED,
                                     project_id=project.id,
                                     workflow_id=0,
                                     input_dataset_id=input_dataset.id,
                                     output_dataset_id=output_dataset.id,
                                     coordinator_id=0)
            dataset_job.set_global_configs(
                dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()}))
            session.add(dataset_job)

            output_data_batch = DataBatch(name='20220101',
                                          dataset_id=output_dataset.id,
                                          event_time=datetime(year=2000, month=1, day=1))
            session.add(output_data_batch)
            session.flush()

            dataset_job_stage = DatasetJobStage(name='20220101-stage0',
                                                dataset_job_id=dataset_job.id,
                                                data_batch_id=output_data_batch.id,
                                                project_id=project.id,
                                                event_time=datetime(year=2000, month=1, day=1),
                                                uuid=resource_uuid())
            session.add(dataset_job_stage)

            session.commit()
            self.project_id = project.id
            self.input_dataset_id = input_dataset.id
            self.output_dataset_id = output_dataset.id
            self.dataset_job_id = dataset_job.id
            self.output_data_batch_id = output_data_batch.id
            self.dataset_job_stage_id = dataset_job_stage.id

    def test_create_dataset_job_stage(self):
        with db.session_scope() as session:
            with self.assertRaises(InvalidArgumentException):
                dataset_job_stage = DatasetJobStageService(session).create_dataset_job_stage(
                    project_id=self.project_id,
                    dataset_job_id=self.dataset_job_id,
                    output_data_batch_id=self.output_data_batch_id)
            dataset_job_stage = session.query(DatasetJobStage).get(self.dataset_job_stage_id)
            dataset_job_stage.state = DatasetJobState.SUCCEEDED
            session.commit()
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageService(session).create_dataset_job_stage(
                project_id=self.project_id,
                dataset_job_id=self.dataset_job_id,
                output_data_batch_id=self.output_data_batch_id)
            session.commit()
            dataset_job_stage_id = dataset_job_stage.id
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            self.assertEqual(dataset_job_stage.name, '20220101-stage1')
            self.assertEqual(dataset_job_stage.event_time, datetime(year=2000, month=1, day=1))
            self.assertEqual(dataset_job_stage.dataset_job_id, self.dataset_job_id)
            self.assertEqual(dataset_job_stage.data_batch_id, self.output_data_batch_id)
            self.assertEqual(dataset_job_stage.project_id, self.project_id)
            dataset_job = session.query(DatasetJob).get(self.dataset_job_id)
            self.assertEqual(dataset_job.state, DatasetJobState.PENDING)
            data_batch = session.query(DataBatch).get(self.output_data_batch_id)
            self.assertEqual(data_batch.latest_parent_dataset_job_stage_id, 2)

    def test_create_dataset_job_stage_as_coordinator(self):
        global_configs = dataset_pb2.DatasetJobGlobalConfigs(global_configs={'test': dataset_pb2.DatasetJobConfig()})
        with db.session_scope() as session:
            with self.assertRaises(InvalidArgumentException):
                dataset_job_stage = DatasetJobStageService(session).create_dataset_job_stage_as_coordinator(
                    project_id=self.project_id,
                    dataset_job_id=self.dataset_job_id,
                    output_data_batch_id=self.output_data_batch_id,
                    global_configs=global_configs)
            dataset_job_stage = session.query(DatasetJobStage).get(self.dataset_job_stage_id)
            dataset_job_stage.state = DatasetJobState.SUCCEEDED
            session.commit()
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageService(session).create_dataset_job_stage_as_coordinator(
                project_id=self.project_id,
                dataset_job_id=self.dataset_job_id,
                output_data_batch_id=self.output_data_batch_id,
                global_configs=global_configs)
            session.commit()
            dataset_job_stage_id = dataset_job_stage.id
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            self.assertEqual(dataset_job_stage.name, '20220101-stage1')
            self.assertEqual(dataset_job_stage.event_time, datetime(year=2000, month=1, day=1))
            self.assertEqual(dataset_job_stage.dataset_job_id, self.dataset_job_id)
            self.assertEqual(dataset_job_stage.data_batch_id, self.output_data_batch_id)
            self.assertEqual(dataset_job_stage.project_id, self.project_id)
            self.assertEqual(dataset_job_stage.get_global_configs(), global_configs)
            self.assertTrue(dataset_job_stage.is_coordinator())
            dataset_job = session.query(DatasetJob).get(self.dataset_job_id)
            self.assertEqual(dataset_job.state, DatasetJobState.PENDING)
            data_batch = session.query(DataBatch).get(self.output_data_batch_id)
            self.assertEqual(data_batch.latest_parent_dataset_job_stage_id, 2)

    def test_create_dataset_job_stage_as_participant(self):
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(self.dataset_job_stage_id)
            dataset_job_stage.state = DatasetJobState.SUCCEEDED
            session.commit()
        with db.session_scope() as session:
            dataset_job_stage = DatasetJobStageService(session).create_dataset_job_stage_as_participant(
                project_id=self.project_id,
                dataset_job_id=self.dataset_job_id,
                output_data_batch_id=self.output_data_batch_id,
                uuid='test dataset_job_stage uuid',
                name='test dataset_job_stage',
                coordinator_id=1)
            session.commit()
            dataset_job_stage_id = dataset_job_stage.id
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(dataset_job_stage_id)
            self.assertEqual(dataset_job_stage.name, 'test dataset_job_stage')
            self.assertEqual(dataset_job_stage.uuid, 'test dataset_job_stage uuid')
            self.assertEqual(dataset_job_stage.coordinator_id, 1)
            self.assertEqual(dataset_job_stage.event_time, datetime(year=2000, month=1, day=1))
            self.assertEqual(dataset_job_stage.dataset_job_id, self.dataset_job_id)
            self.assertEqual(dataset_job_stage.data_batch_id, self.output_data_batch_id)
            self.assertEqual(dataset_job_stage.project_id, self.project_id)
            dataset_job = session.query(DatasetJob).get(self.dataset_job_id)
            self.assertEqual(dataset_job.state, DatasetJobState.PENDING)
            data_batch = session.query(DataBatch).get(self.output_data_batch_id)
            self.assertEqual(data_batch.latest_parent_dataset_job_stage_id, 2)

    def test_start_dataset_job_stage(self):
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(self.dataset_job_stage_id)
            DatasetJobStageService(session).start_dataset_job_stage(dataset_job_stage)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.RUNNING)
            self.assertEqual(dataset_job_stage.dataset_job.state, DatasetJobState.RUNNING)

    def test_finish_dataset_job_stage(self):
        with db.session_scope() as session:
            dataset_job_stage = session.query(DatasetJobStage).get(self.dataset_job_stage_id)
            DatasetJobStageService(session).finish_dataset_job_stage(dataset_job_stage, DatasetJobState.STOPPED)
            self.assertEqual(dataset_job_stage.state, DatasetJobState.STOPPED)
            self.assertEqual(dataset_job_stage.dataset_job.state, DatasetJobState.STOPPED)

            with self.assertRaises(ValueError):
                DatasetJobStageService(session).finish_dataset_job_stage(dataset_job_stage, DatasetJobState.RUNNING)


class DataReaderTest(unittest.TestCase):

    def test_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = f'{temp_dir}/dataset'
            batch_name = '20220101'
            meta_file = DatasetDirectory(dataset_path=dataset_path).batch_meta_file(batch_name=batch_name)

            # test no meta
            reader = DataReader(dataset_path=dataset_path).metadata(batch_name=batch_name)
            self.assertEqual(reader.metadata, {})

            # test get meta
            meta_info = {
                'dtypes': [{
                    'key': 'f01',
                    'value': 'bigint'
                }],
                'sample': [
                    [1],
                    [0],
                ],
                'count': 1000,
                'metrics': {
                    'f01': {
                        'count': '2',
                        'mean': '0.0015716767309123998',
                        'stddev': '0.03961485047808605',
                        'min': '0',
                        'max': '1',
                        'missing_count': '0'
                    }
                },
                'hist': {
                    'x': [
                        0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9,
                        1
                    ],
                    'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
                }
            }
            Path(meta_file.split('/_META')[0]).mkdir(parents=True)
            with open(meta_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(meta_info))
            reader = DataReader(dataset_path=dataset_path).metadata(batch_name=batch_name)
            self.assertEqual(reader.metadata, meta_info)

    def test_image_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = f'{temp_dir}/dataset'
            batch_name = '20220101'
            dataset_directory = DatasetDirectory(dataset_path=dataset_path)
            meta_file = dataset_directory.batch_meta_file(batch_name=batch_name)
            thumbnail_dir_path = dataset_directory.thumbnails_path(batch_name=batch_name)

            # test no meta
            reader = DataReader(dataset_path=dataset_path).image_metadata(thumbnail_dir_path=thumbnail_dir_path,
                                                                          batch_name=batch_name)
            self.assertEqual(reader.metadata, {})
            self.assertEqual(reader.thumbnail_dir_path, thumbnail_dir_path)

            # test get meta
            meta_info = {
                'dtypes': [{
                    'key': 'f01',
                    'value': 'bigint'
                }],
                'sample': [
                    [1],
                    [0],
                ],
                'count': 1000,
                'metrics': {
                    'f01': {
                        'count': '2',
                        'mean': '0.0015716767309123998',
                        'stddev': '0.03961485047808605',
                        'min': '0',
                        'max': '1',
                        'missing_count': '0'
                    }
                },
                'hist': {
                    'x': [
                        0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9,
                        1
                    ],
                    'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
                }
            }
            Path(meta_file.split('/_META')[0]).mkdir(parents=True)
            with open(meta_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(meta_info))
            reader = DataReader(dataset_path=dataset_path).image_metadata(thumbnail_dir_path=thumbnail_dir_path,
                                                                          batch_name=batch_name)
            self.assertEqual(reader.metadata, meta_info)
            self.assertEqual(reader.thumbnail_dir_path, thumbnail_dir_path)


if __name__ == '__main__':
    unittest.main()
