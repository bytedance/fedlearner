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
import os
import tempfile
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
import urllib
import unittest
from unittest.mock import patch, MagicMock, ANY, PropertyMock
from google.protobuf.struct_pb2 import Value

from collections import namedtuple
from marshmallow.exceptions import ValidationError
from tensorflow.io import gfile

from envs import Envs
from testing.common import BaseTestCase
from testing.dataset import FakeDatasetJobConfiger, FakeFederatedDatasetJobConfiger

from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.apis import _parse_data_source_url, _path_authority_validator
from fedlearner_webconsole.dataset.models import (Dataset, DatasetJob, DatasetJobKind, DatasetJobSchedulerState,
                                                  DatasetJobStage, ImportType, DatasetKindV2, DatasetSchemaChecker,
                                                  DatasetJobState, StoreFormat, DatasetType, ResourceState, DataBatch,
                                                  DatasetFormat, BatchState, DataSourceType, DataSource)
from fedlearner_webconsole.dataset.dataset_directory import DatasetDirectory
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant
from fedlearner_webconsole.proto import dataset_pb2, service_pb2, setting_pb2
from fedlearner_webconsole.proto.project_pb2 import ParticipantInfo, ParticipantsInfo
from fedlearner_webconsole.proto.rpc.v2.resource_service_pb2 import ListDatasetsResponse
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.algorithm_pb2 import FileTreeNode

FakeFileStatistics = namedtuple('FakeFileStatistics', ['length', 'mtime_nsec', 'is_directory'])


def fake_get_items(*args, **kwargs):
    return {}, []


def fake_export_task_result(*args, **kwargs):
    return {}


def fake_isdir(*args, **kwargs):
    path = kwargs.get('path')
    return (path in [
        'file:///data/test', 'hdfs:///home/', 'hdfs:///home/20220801', 'hdfs:///home/20220802',
        'hdfs:///home/20220803-15', 'hdfs:///home/2022080316'
    ])


class DatasetApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        STORAGE_ROOT = tempfile.gettempdir()

    def setUp(self):
        super().setUp()
        self._storage_root = Envs.STORAGE_ROOT
        self._file_manager = FileManager()
        with db.session_scope() as session:
            project = Project(name='test-project')
            session.add(project)
            session.flush([project])
            participant = Participant(id=project.id, name='test_participant', domain_name='fake_domain_name')
            session.add(participant)
            project_participant = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            session.add(project_participant)
            workflow = Workflow(state=WorkflowState.COMPLETED, name='workflow_generate_by_dataset_job')
            session.add(workflow)

            session.commit()

        with db.session_scope() as session:
            self.default_dataset1 = Dataset(name='default dataset1',
                                            creator_username='test',
                                            uuid='default dataset1 uuid',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment1',
                                            path='/data/dataset/123',
                                            project_id=1,
                                            dataset_kind=DatasetKindV2.RAW,
                                            created_at=datetime(2012, 1, 14, 12, 0, 5))
            meta_info = dataset_pb2.DatasetMetaInfo(value=100,
                                                    schema_checkers=[
                                                        DatasetSchemaChecker.RAW_ID_CHECKER.value,
                                                        DatasetSchemaChecker.NUMERIC_COLUMNS_CHECKER.value
                                                    ])
            self.default_dataset1.set_meta_info(meta_info)
            session.add(self.default_dataset1)
            session.flush()
            default_dataset_job_1 = DatasetJob(workflow_id=workflow.id,
                                               uuid=resource_uuid(),
                                               project_id=project.id,
                                               kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                               input_dataset_id=100,
                                               output_dataset_id=self.default_dataset1.id,
                                               state=DatasetJobState.FAILED)
            session.add(default_dataset_job_1)
            session.commit()
        with db.session_scope() as session:
            self.default_dataset2 = Dataset(name='default dataset2',
                                            creator_username='test',
                                            dataset_type=DatasetType.STREAMING,
                                            comment='test comment2',
                                            path=os.path.join(tempfile.gettempdir(), 'dataset/123'),
                                            project_id=project.id,
                                            dataset_kind=DatasetKindV2.PROCESSED,
                                            dataset_format=DatasetFormat.TABULAR.value,
                                            created_at=datetime(2012, 1, 14, 12, 0, 6))
            session.add(self.default_dataset2)
            session.flush([self.default_dataset2])
            data_batch = DataBatch(event_time=datetime.now(),
                                   comment='comment',
                                   state=BatchState.NEW,
                                   dataset_id=self.default_dataset2.id,
                                   path='/data/dataset/123/batch_test_batch')
            session.add(data_batch)
            session.flush()
            default_dataset_job_2 = DatasetJob(workflow_id=workflow.id,
                                               uuid=resource_uuid(),
                                               project_id=project.id,
                                               kind=DatasetJobKind.DATA_ALIGNMENT,
                                               input_dataset_id=100,
                                               output_dataset_id=self.default_dataset2.id)
            session.add(default_dataset_job_2)
            default_dataset_job_3 = DatasetJob(workflow_id=workflow.id,
                                               uuid=resource_uuid(),
                                               project_id=project.id,
                                               kind=DatasetJobKind.ANALYZER,
                                               input_dataset_id=self.default_dataset2.id,
                                               output_dataset_id=self.default_dataset2.id)
            session.add(default_dataset_job_3)
            session.commit()

        with db.session_scope() as session:
            workflow = Workflow(id=100, state=WorkflowState.COMPLETED, name='fake_workflow')
            dataset = Dataset(id=3,
                              name='dataset',
                              creator_username='test',
                              dataset_type=DatasetType.STREAMING,
                              comment='comment',
                              path=os.path.join(tempfile.gettempdir(), 'dataset/321'),
                              project_id=3,
                              created_at=datetime(2012, 1, 14, 12, 0, 7))
            session.add(workflow)
            session.add(dataset)
            session.flush()
            default_dataset_job_4 = DatasetJob(workflow_id=workflow.id,
                                               uuid=resource_uuid(),
                                               project_id=project.id,
                                               kind=DatasetJobKind.DATA_ALIGNMENT,
                                               input_dataset_id=100,
                                               output_dataset_id=dataset.id)
            session.add(default_dataset_job_4)
            session.commit()

    def test_get_dataset(self):
        get_response = self.get_helper(f'/api/v2/datasets/{self.default_dataset1.id}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            get_response,
            {
                'id': 1,
                'name': 'default dataset1',
                'creator_username': 'test',
                'comment': 'test comment1',
                'path': '/data/dataset/123',
                'deleted_at': 0,
                'dataset_kind': 'RAW',
                'is_published': False,
                'project_id': 1,
                'dataset_format': DatasetFormat.TABULAR.name,
                'num_feature': 0,
                'num_example': 0,
                'state_frontend': ResourceState.FAILED.value,
                'file_size': 0,
                'parent_dataset_job_id': 1,
                'data_source': ANY,
                'workflow_id': 1,
                'value': 100,
                'schema_checkers': ['RAW_ID_CHECKER', 'NUMERIC_COLUMNS_CHECKER'],
                'dataset_type': 'STREAMING',
                'import_type': 'COPY',
                'store_format': 'TFRECORDS',
                'analyzer_dataset_job_id': 0,
                'publish_frontend_state': 'UNPUBLISHED',
                'auth_frontend_state': 'AUTH_APPROVED',
                'local_auth_status': 'PENDING',
                'participants_info': {
                    'participants_map': {}
                },
            },
            ignore_fields=[
                'created_at',
                'updated_at',
                'uuid',
            ],
        )

    def test_get_internal_processed_dataset(self):
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

        get_response = self.get_helper('/api/v2/datasets/10')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            get_response,
            {
                'id': 10,
                'project_id': 1,
                'name': 'default dataset',
                'path': '/data/dataset/123',
                'comment': 'test comment',
                'dataset_format': 'TABULAR',
                'state_frontend': 'SUCCEEDED',
                'dataset_kind': 'INTERNAL_PROCESSED',
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
                'auth_frontend_state': 'AUTH_APPROVED',
                'local_auth_status': 'AUTHORIZED',
                'participants_info': {
                    'participants_map': {}
                },
            },
            ignore_fields=[
                'uuid',
                'created_at',
                'updated_at',
            ],
        )

    def test_get_dataset_not_found(self):
        get_response = self.get_helper('/api/v2/datasets/10086')
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_datasets(self):
        with db.session_scope() as session:
            default_dataset_job_4 = session.query(DatasetJob).get(4)
            default_dataset_job_4.kind = DatasetJobKind.ANALYZER
            default_dataset_job_4.input_dataset_id = 3

            default_data_source = DataSource(id=4,
                                             name='default data_source',
                                             creator_username='test',
                                             uuid='default data_source uuid',
                                             comment='test comment1',
                                             path='/data/dataset/123',
                                             project_id=1,
                                             dataset_kind=DatasetKindV2.SOURCE,
                                             created_at=datetime(2012, 1, 14, 12, 0, 1))
            session.add(default_data_source)
            session.commit()
        get_response = self.get_helper('/api/v2/datasets')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(datasets, [{
            'id': 3,
            'project_id': 3,
            'comment': 'comment',
            'created_at': 1326542407,
            'creator_username': 'test',
            'data_source': ANY,
            'dataset_format': 'TABULAR',
            'dataset_kind': 'RAW',
            'dataset_type': 'STREAMING',
            'file_size': 0,
            'import_type': 'COPY',
            'is_published': False,
            'name': 'dataset',
            'num_example': 0,
            'path': ANY,
            'state_frontend': 'FAILED',
            'store_format': 'TFRECORDS',
            'total_value': 0,
            'uuid': '',
            'publish_frontend_state': 'UNPUBLISHED',
            'auth_frontend_state': 'AUTH_APPROVED',
            'local_auth_status': 'PENDING',
            'participants_info': {
                'participants_map': {}
            },
        }, {
            'id': 2,
            'project_id': 1,
            'name': 'default dataset2',
            'creator_username': 'test',
            'created_at': 1326542406,
            'path': ANY,
            'dataset_format': 'TABULAR',
            'comment': 'test comment2',
            'state_frontend': 'PENDING',
            'dataset_kind': 'PROCESSED',
            'data_source': ANY,
            'file_size': 0,
            'is_published': False,
            'num_example': 0,
            'uuid': '',
            'total_value': 0,
            'store_format': 'TFRECORDS',
            'dataset_type': 'STREAMING',
            'import_type': 'COPY',
            'publish_frontend_state': 'UNPUBLISHED',
            'auth_frontend_state': 'AUTH_APPROVED',
            'local_auth_status': 'PENDING',
            'participants_info': {
                'participants_map': {}
            },
        }, {
            'id': 1,
            'project_id': 1,
            'name': 'default dataset1',
            'creator_username': 'test',
            'created_at': 1326542405,
            'path': '/data/dataset/123',
            'dataset_format': 'TABULAR',
            'comment': 'test comment1',
            'state_frontend': 'FAILED',
            'uuid': 'default dataset1 uuid',
            'dataset_kind': 'RAW',
            'file_size': 0,
            'is_published': False,
            'num_example': 0,
            'data_source': ANY,
            'total_value': 0,
            'store_format': 'TFRECORDS',
            'dataset_type': 'STREAMING',
            'import_type': 'COPY',
            'publish_frontend_state': 'UNPUBLISHED',
            'auth_frontend_state': 'AUTH_APPROVED',
            'local_auth_status': 'PENDING',
            'participants_info': {
                'participants_map': {}
            },
        }, {
            'id': 4,
            'project_id': 1,
            'name': 'default data_source',
            'creator_username': 'test',
            'comment': 'test comment1',
            'created_at': 1326542401,
            'path': '/data/dataset/123',
            'data_source': ANY,
            'dataset_format': 'TABULAR',
            'dataset_kind': 'SOURCE',
            'dataset_type': 'PSI',
            'file_size': 0,
            'import_type': 'COPY',
            'is_published': False,
            'num_example': 0,
            'state_frontend': 'FAILED',
            'store_format': 'TFRECORDS',
            'total_value': 0,
            'uuid': 'default data_source uuid',
            'publish_frontend_state': 'UNPUBLISHED',
            'auth_frontend_state': 'AUTH_APPROVED',
            'local_auth_status': 'PENDING',
            'participants_info': {
                'participants_map': {}
            },
        }])
        self.assertEqual(
            json.loads(get_response.data).get('page_meta'), {
                'current_page': 1,
                'page_size': 10,
                'total_pages': 1,
                'total_items': 4
            })

        with db.session_scope() as session:
            default_dataset_job_4 = session.query(DatasetJob).get(4)
            default_dataset_job_4.kind = DatasetJobKind.DATA_ALIGNMENT
            default_dataset_job_4.input_dataset_id = 100
            session.commit()

        # test sorter
        sorter_param = urllib.parse.quote('created_at asc')
        get_response = self.get_helper(f'/api/v2/datasets?order_by={sorter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 4)
        self.assertEqual([dataset.get('id') for dataset in datasets], [4, 1, 2, 3])

        fake_sorter_param = urllib.parse.quote('fake_time asc')
        get_response = self.get_helper(f'/api/v2/datasets?order_by={fake_sorter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.BAD_REQUEST)

        # test filter
        filter_param = urllib.parse.quote('(and(project_id=1)(name~="default"))')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 3)
        self.assertEqual([dataset.get('name') for dataset in datasets],
                         ['default dataset2', 'default dataset1', 'default data_source'])

        filter_param = urllib.parse.quote('(and(project_id=1)(dataset_format:["TABULAR"])(dataset_kind:["RAW"]))')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('name'), 'default dataset1')

        filter_param = urllib.parse.quote('(dataset_format="IMAGE")')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 0)

        filter_param = urllib.parse.quote('(dataset_format="UNKOWN")')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.BAD_REQUEST)

        filter_param = urllib.parse.quote('(is_published=false)')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 4)

        # test state_frontend
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.state = DatasetJobState.SUCCEEDED
            session.commit()
        get_response = self.get_helper('/api/v2/datasets?state_frontend=SUCCEEDED')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('name'), 'default dataset1')

    def test_get_datasets_by_publish_frontend_state(self):
        with db.session_scope() as session:
            default_dataset_1 = session.query(Dataset).get(1)
            default_dataset_1.ticket_status = None
            default_dataset_1.is_published = False
            default_dataset_2 = session.query(Dataset).get(2)
            default_dataset_2.ticket_status = TicketStatus.PENDING
            default_dataset_2.is_published = True
            default_dataset_3 = session.query(Dataset).get(3)
            default_dataset_3.ticket_status = TicketStatus.APPROVED
            default_dataset_3.is_published = True
            session.commit()
        filter_param = urllib.parse.quote('(publish_frontend_state="UNPUBLISHED")')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('id'), 1)

        filter_param = urllib.parse.quote('(publish_frontend_state="TICKET_PENDING")')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('id'), 2)

        filter_param = urllib.parse.quote('(publish_frontend_state="PUBLISHED")')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('id'), 3)

    def test_get_datasets_by_auth_state(self):
        with db.session_scope() as session:
            default_dataset_1 = session.query(Dataset).get(1)
            default_dataset_1.auth_status = AuthStatus.AUTHORIZED
            default_dataset_2 = session.query(Dataset).get(2)
            default_dataset_2.auth_status = AuthStatus.PENDING
            default_dataset_3 = session.query(Dataset).get(3)
            default_dataset_3.auth_status = AuthStatus.WITHDRAW
            session.commit()
        filter_param = urllib.parse.quote('(auth_status:["AUTHORIZED", "WITHDRAW"])')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 2)
        self.assertEqual([dataset.get('id') for dataset in datasets], [3, 1])

        with db.session_scope() as session:
            default_dataset_2 = session.query(Dataset).get(2)
            default_dataset_2.auth_status = None
            session.commit()
        filter_param = urllib.parse.quote('(auth_status:["AUTHORIZED"])')
        get_response = self.get_helper(f'/api/v2/datasets?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 2)
        self.assertEqual([dataset.get('id') for dataset in datasets], [2, 1])

    def test_get_internal_processed_datasets(self):
        with db.session_scope() as session:
            internal_processed_dataset = Dataset(id=10,
                                                 uuid=resource_uuid(),
                                                 name='internal_processed dataset',
                                                 dataset_type=DatasetType.PSI,
                                                 comment='test comment',
                                                 path='/data/dataset/123',
                                                 project_id=1,
                                                 dataset_kind=DatasetKindV2.INTERNAL_PROCESSED,
                                                 is_published=False,
                                                 auth_status=AuthStatus.AUTHORIZED)
            session.add(internal_processed_dataset)

            dataset_job = session.query(DatasetJob).get(2)
            dataset_job.state = DatasetJobState.SUCCEEDED

            session.commit()

        get_response = self.get_helper('/api/v2/datasets?state_frontend=SUCCEEDED')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 2)
        self.assertCountEqual([dataset.get('name') for dataset in datasets],
                              ['default dataset2', 'internal_processed dataset'])

        filter_param = urllib.parse.quote('(dataset_kind:["PROCESSED"])')
        get_response = self.get_helper(f'/api/v2/datasets?state_frontend=SUCCEEDED&filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('name'), 'default dataset2')

        get_response = self.get_helper('/api/v2/datasets?state_frontend=FAILED')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('name'), 'default dataset1')

    def test_get_datasets_by_time_range(self):
        with db.session_scope() as session:
            default_dataset_1 = session.query(Dataset).get(1)
            default_dataset_1.parent_dataset_job.time_range = timedelta(days=1)
            default_dataset_2 = session.query(Dataset).get(2)
            default_dataset_2.parent_dataset_job.time_range = timedelta(hours=1)
            session.commit()
        get_response = self.get_helper('/api/v2/datasets?cron_interval=DAYS')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('id'), 1)
        get_response = self.get_helper('/api/v2/datasets?cron_interval=HOURS')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get('id'), 2)
        get_response = self.get_helper('/api/v2/datasets')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 3)

    def test_change_dataset_comment(self):
        get_response = self.patch_helper(f'/api/v2/datasets/{self.default_dataset1.id}', data={'comment': 'test api'})
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(self.default_dataset1.id)
            self.assertEqual(dataset.comment, 'test api')

    def test_preview_dataset(self):
        with db.session_scope() as session:
            tmp_path = tempfile.gettempdir()
            self.batch_path = os.path.join(tmp_path, 'dataset/20211228_161352_train-ds/batch/20211228_081351')
            self.default_databatch1 = DataBatch(name='20220101',
                                                id=111,
                                                event_time=datetime.now(),
                                                comment='comment',
                                                state=BatchState.NEW,
                                                dataset_id=1,
                                                path=self.batch_path)
            session.add(self.default_databatch1)
            session.commit()
        with db.session_scope() as session:
            tmp_path = tempfile.gettempdir()
            self.batch_path = os.path.join(tmp_path, 'dataset/20211228_161352_train-ds/batch/20211228_081352')
            self.default_databatch2 = DataBatch(name='20220102',
                                                id=222,
                                                event_time=datetime.now(),
                                                comment='comment',
                                                state=BatchState.NEW,
                                                dataset_id=2,
                                                path=self.batch_path)
            session.add(self.default_databatch2)
            session.commit()
        meta_file = DatasetDirectory(dataset_path=self.default_dataset2.path).batch_meta_file(batch_name='20220101')
        gfile.makedirs(meta_file.split('/_META')[0])
        meta_data = {
            'dtypes': [{
                'key': 'f01',
                'value': 'bigint'
            }],
            'sample': [
                [
                    1,
                ],
                [
                    0,
                ],
            ],
            'count': 0,
            'features': {
                'f01': {
                    'count': '2',
                    'mean': '0.0015716767309123998',
                    'stddev': '0.03961485047808605',
                    'min': '0',
                    'max': '1',
                    'missing_count': '0'
                },
            },
            'hist': {
                'f01': {
                    'x': [
                        0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9,
                        1
                    ],
                    'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
                },
            },
        }
        with gfile.GFile(meta_file, 'w') as f:
            f.write(json.dumps(meta_data))

        response = self.get_helper('/api/v2/datasets/2/preview?batch_id=111')
        self.assertEqual(response.status_code, 200)
        preview_data = self.get_response_data(response)
        golden_preview = {
            'dtypes': [{
                'key': 'f01',
                'value': 'bigint'
            }],
            'sample': [
                [1],
                [0],
            ],
            'num_example': 0,
            'metrics': {
                'f01': {
                    'count': '2',
                    'mean': '0.0015716767309123998',
                    'stddev': '0.03961485047808605',
                    'min': '0',
                    'max': '1',
                    'missing_count': '0'
                },
            },
        }
        self.assertEqual(preview_data, golden_preview, 'should has preview data')

    @patch('fedlearner_webconsole.dataset.services.get_dataset_path')
    def test_post_raw_datasets(self, mock_get_dataset_path: MagicMock):
        name = 'test_dataset'
        dataset_path = os.path.join(self._storage_root, 'dataset/20200608_060606_test-post-dataset')
        mock_get_dataset_path.return_value = dataset_path
        dataset_type = DatasetType.PSI.value
        comment = 'test comment'
        create_response = self.post_helper('/api/v2/datasets',
                                           data={
                                               'name': name,
                                               'dataset_type': dataset_type,
                                               'comment': comment,
                                               'project_id': 1,
                                               'dataset_format': DatasetFormat.TABULAR.name,
                                               'kind': DatasetKindV2.RAW.value,
                                               'need_publish': True,
                                               'value': 100,
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.CREATED)

        self.assertResponseDataEqual(
            create_response,
            {
                'id': ANY,
                'name': 'test_dataset',
                'creator_username': 'ada',
                'comment': comment,
                'path': dataset_path,
                'deleted_at': 0,
                'data_source': '',
                'project_id': 1,
                'dataset_kind': DatasetKindV2.RAW.name,
                'is_published': False,
                'dataset_format': DatasetFormat.TABULAR.name,
                'state_frontend': ResourceState.FAILED.value,
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'parent_dataset_job_id': 0,
                'workflow_id': 0,
                'value': 100,
                'schema_checkers': [],
                'dataset_type': DatasetType.PSI.value,
                'import_type': ImportType.COPY.value,
                'store_format': StoreFormat.TFRECORDS.value,
                'analyzer_dataset_job_id': 0,
                'publish_frontend_state': 'UNPUBLISHED',
                'auth_frontend_state': 'AUTH_APPROVED',
                'local_auth_status': 'AUTHORIZED',
                'participants_info': {
                    'participants_map': {}
                },
            },
            ignore_fields=['created_at', 'updated_at', 'uuid'],
        )
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).outerjoin(
                Dataset, Dataset.id == DataBatch.dataset_id).filter(Dataset.name == name).first()
            self.assertIsNone(data_batch)

    @patch('fedlearner_webconsole.dataset.services.get_dataset_path')
    def test_post_processed_datasets(self, mock_get_dataset_path: MagicMock):
        name = 'test_dataset'
        dataset_path = os.path.join(self._storage_root, 'dataset/20200608_060606_test-post-dataset')
        mock_get_dataset_path.return_value = dataset_path
        dataset_type = DatasetType.PSI.value
        comment = 'test comment'

        # test bad request
        create_response = self.post_helper('/api/v2/datasets',
                                           data={
                                               'name': name,
                                               'dataset_type': dataset_type,
                                               'comment': comment,
                                               'project_id': 1,
                                               'dataset_format': DatasetFormat.TABULAR.name,
                                               'kind': DatasetKindV2.PROCESSED.value,
                                               'need_publish': True,
                                               'value': 100,
                                               'is_published': False
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.BAD_REQUEST)

        # test pass
        create_response = self.post_helper('/api/v2/datasets',
                                           data={
                                               'name': name,
                                               'dataset_type': dataset_type,
                                               'comment': comment,
                                               'project_id': 1,
                                               'dataset_format': DatasetFormat.TABULAR.name,
                                               'kind': DatasetKindV2.PROCESSED.value,
                                               'is_published': True,
                                               'value': 100,
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.CREATED)

        self.assertResponseDataEqual(
            create_response,
            {
                'id': ANY,
                'name': 'test_dataset',
                'creator_username': 'ada',
                'comment': comment,
                'path': dataset_path,
                'deleted_at': 0,
                'data_source': '',
                'project_id': 1,
                'dataset_kind': DatasetKindV2.PROCESSED.name,
                'is_published': True,
                'dataset_format': DatasetFormat.TABULAR.name,
                'state_frontend': ResourceState.FAILED.value,
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'parent_dataset_job_id': 0,
                'workflow_id': 0,
                'value': 100,
                'schema_checkers': [],
                'dataset_type': DatasetType.PSI.value,
                'import_type': ImportType.COPY.value,
                'store_format': StoreFormat.TFRECORDS.value,
                'analyzer_dataset_job_id': 0,
                'publish_frontend_state': 'PUBLISHED',
                'auth_frontend_state': 'AUTH_APPROVED',
                'local_auth_status': 'AUTHORIZED',
                'participants_info': {
                    'participants_map': {}
                },
            },
            ignore_fields=['created_at', 'updated_at', 'uuid'],
        )
        with db.session_scope() as session:
            data_batch: DataBatch = session.query(DataBatch).outerjoin(
                Dataset, Dataset.id == DataBatch.dataset_id).filter(Dataset.name == name).first()
            self.assertIsNone(data_batch)
            dataset = session.query(Dataset).filter(Dataset.name == name).first()
            self.assertEqual(dataset.ticket_status, TicketStatus.APPROVED)

    @patch('fedlearner_webconsole.dataset.services.get_dataset_path')
    def test_post_datasets_with_checkers(self, mock_get_dataset_path: MagicMock):
        dataset_path = os.path.join(self._storage_root, 'dataset/20200608_060606_test-post-dataset')
        mock_get_dataset_path.return_value = dataset_path
        create_response = self.post_helper('/api/v2/datasets',
                                           data={
                                               'name': 'fake_dataset',
                                               'comment': 'comment',
                                               'project_id': 1,
                                               'dataset_format': DatasetFormat.TABULAR.name,
                                               'kind': DatasetKindV2.RAW.value,
                                               'schema_checkers': ['RAW_ID_CHECKER', 'NUMERIC_COLUMNS_CHECKER']
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.CREATED)

        self.assertResponseDataEqual(
            create_response,
            {
                'id': 4,
                'name': 'fake_dataset',
                'creator_username': 'ada',
                'comment': 'comment',
                'path': dataset_path,
                'deleted_at': 0,
                'data_source': '',
                'project_id': 1,
                'dataset_kind': DatasetKindV2.RAW.name,
                'is_published': False,
                'dataset_format': DatasetFormat.TABULAR.name,
                'state_frontend': ResourceState.FAILED.value,
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'parent_dataset_job_id': 0,
                'workflow_id': 0,
                'value': 0,
                'schema_checkers': ['RAW_ID_CHECKER', 'NUMERIC_COLUMNS_CHECKER'],
                'dataset_type': 'PSI',
                'import_type': 'COPY',
                'store_format': 'TFRECORDS',
                'analyzer_dataset_job_id': 0,
                'publish_frontend_state': 'UNPUBLISHED',
                'auth_frontend_state': 'AUTH_APPROVED',
                'local_auth_status': 'AUTHORIZED',
                'participants_info': {
                    'participants_map': {}
                },
            },
            ignore_fields=['created_at', 'updated_at', 'uuid'],
        )
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(4)
            meta_info = dataset.get_meta_info()
            self.assertEqual(list(meta_info.schema_checkers), ['RAW_ID_CHECKER', 'NUMERIC_COLUMNS_CHECKER'])

    def _fake_schema_check_test_data(self):
        # schema check test
        self.dataset_dir = tempfile.mkdtemp()
        self.dataset_csv = Path(self.dataset_dir).joinpath('test.csv')
        self.dataset_json = Path(self.dataset_dir).joinpath('validation_jsonschema.json')
        self.error_dir = Path(self.dataset_dir).joinpath('error')
        self.error_dir.mkdir()
        self.error_json = self.error_dir.joinpath('schema_error.json')

        with db.session_scope() as session:
            self.schema_check_dataset = Dataset(name='schema_check_dataset',
                                                dataset_type=DatasetType.STREAMING,
                                                comment='schema check dataset',
                                                path=str(self.dataset_dir),
                                                project_id=1)
            session.add(self.schema_check_dataset)
            session.flush()
            self.schema_check_batch = DataBatch(dataset_id=self.schema_check_dataset.id,
                                                event_time=datetime(2021, 10, 28, 16, 37, 37),
                                                comment='schema check batch')
            session.add(self.schema_check_batch)
            session.commit()

    def __del__(self):
        # delete the dataset path, created in function: test_post_datasets
        dataset_path = os.path.join(self._storage_root, 'dataset/20200608_060606_test-post-dataset')
        if self._file_manager.isdir(dataset_path):
            self._file_manager.remove(dataset_path)


class DatasetExportApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test_project')
            session.add(project)
            session.flush([project])

            dataset = Dataset(id=1,
                              name='test_dataset',
                              dataset_type=DatasetType.PSI,
                              uuid='dataset uuid',
                              comment='comment',
                              path='/data/dataset/321',
                              project_id=project.id,
                              dataset_format=DatasetFormat.NONE_STRUCTURED.value,
                              store_format=StoreFormat.UNKNOWN,
                              dataset_kind=DatasetKindV2.PROCESSED)
            data_batch = DataBatch(id=1, name='0', comment='comment', dataset_id=1, path='/data/dataset/321/batch/0')
            session.add_all([dataset, data_batch])

            streaming_dataset = Dataset(id=2,
                                        name='test_streaming_dataset',
                                        dataset_type=DatasetType.STREAMING,
                                        uuid='streaming dataset uuid',
                                        comment='comment',
                                        path='/data/dataset/streaming_dataset',
                                        project_id=project.id,
                                        dataset_format=DatasetFormat.TABULAR.value,
                                        store_format=StoreFormat.TFRECORDS,
                                        dataset_kind=DatasetKindV2.PROCESSED)
            streaming_data_batch_1 = DataBatch(id=2,
                                               name='20220101',
                                               comment='comment',
                                               dataset_id=2,
                                               path='/data/dataset/321/batch/20220101',
                                               event_time=datetime(2022, 1, 1))
            streaming_data_batch_2 = DataBatch(id=3,
                                               name='20220102',
                                               comment='comment',
                                               dataset_id=2,
                                               path='/data/dataset/321/batch/20220102',
                                               event_time=datetime(2022, 1, 2))
            session.add_all([streaming_dataset, streaming_data_batch_1, streaming_data_batch_2])

            session.commit()

    @patch('fedlearner_webconsole.dataset.apis.SettingService.get_system_info',
           lambda: setting_pb2.SystemInfo(pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.apis.Envs.STORAGE_ROOT', '/data')
    @patch('fedlearner_webconsole.utils.file_manager.FileManager.isdir', lambda *args: True)
    @patch('fedlearner_webconsole.dataset.models.DataBatch.is_available', lambda _: True)
    def test_export_dataset_none_streaming(self):
        export_path = '/data/user_home/export_dataset'
        resp = self.post_helper('/api/v2/datasets/1:export', {
            'export_path': export_path,
            'batch_id': 1,
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        resp_data = self.get_response_data(resp)
        self.assertEqual(resp_data, {'export_dataset_id': 3, 'dataset_job_id': 1})
        export_dataset_name = 'export-test_dataset-0-0'
        with db.session_scope() as session:
            export_dataset: Dataset = session.query(Dataset).filter(Dataset.name == export_dataset_name).first()
            self.assertEqual(export_dataset.dataset_kind, DatasetKindV2.EXPORTED)
            self.assertEqual(export_dataset.store_format, StoreFormat.UNKNOWN)
            self.assertEqual(export_dataset.dataset_type, DatasetType.PSI)
            self.assertEqual(export_dataset.path, 'file://' + export_path)
            self.assertFalse(export_dataset.is_published)
            batch = export_dataset.get_single_batch()
            self.assertEqual(batch.batch_name, '0')
            self.assertEqual(batch.path, 'file://' + export_path + '/batch/0')
            dataset_job: DatasetJob = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.kind, DatasetJobKind.EXPORT)
            self.assertEqual(
                dataset_job.get_global_configs(),
                dataset_pb2.DatasetJobGlobalConfigs(
                    global_configs={'test_domain': dataset_pb2.DatasetJobConfig(dataset_uuid='dataset uuid')}))
            dataset_job_stagees = dataset_job.dataset_job_stages
            self.assertEqual(len(dataset_job_stagees), 1)
            self.assertEqual(dataset_job_stagees[0].data_batch_id, batch.id)

    @patch('fedlearner_webconsole.dataset.apis.SettingService.get_system_info',
           lambda: setting_pb2.SystemInfo(pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.apis.Envs.STORAGE_ROOT', '/data')
    @patch('fedlearner_webconsole.utils.file_manager.FileManager.isdir', lambda *args: True)
    @patch('fedlearner_webconsole.dataset.models.DataBatch.is_available', lambda _: True)
    def test_export_dataset_streaming(self):
        export_path = '/data/user_home/export_dataset'
        export_path_with_space = ' ' + export_path + ' '
        resp = self.post_helper('/api/v2/datasets/2:export', {'export_path': export_path_with_space})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        resp_data = self.get_response_data(resp)
        self.assertEqual(resp_data, {'export_dataset_id': 3, 'dataset_job_id': 1})
        export_dataset_name = 'export-test_streaming_dataset-0'
        with db.session_scope() as session:
            export_dataset: Dataset = session.query(Dataset).filter(Dataset.name == export_dataset_name).first()
            self.assertEqual(export_dataset.dataset_kind, DatasetKindV2.EXPORTED)
            self.assertEqual(export_dataset.store_format, StoreFormat.CSV)
            self.assertEqual(export_dataset.dataset_type, DatasetType.STREAMING)
            self.assertEqual(export_dataset.path, 'file://' + export_path)
            self.assertFalse(export_dataset.is_published)
            batches = export_dataset.data_batches
            self.assertEqual(len(batches), 2)
            self.assertEqual(batches[0].batch_name, '20220102')
            self.assertEqual(batches[0].path, 'file://' + export_path + '/batch/20220102')
            self.assertEqual(batches[0].event_time, datetime(2022, 1, 2))
            self.assertEqual(batches[1].batch_name, '20220101')
            self.assertEqual(batches[1].path, 'file://' + export_path + '/batch/20220101')
            self.assertEqual(batches[1].event_time, datetime(2022, 1, 1))
            dataset_job: DatasetJob = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.kind, DatasetJobKind.EXPORT)
            self.assertEqual(
                dataset_job.get_global_configs(),
                dataset_pb2.DatasetJobGlobalConfigs(
                    global_configs={'test_domain': dataset_pb2.DatasetJobConfig(
                        dataset_uuid='streaming dataset uuid')}))
            dataset_job_stagees = dataset_job.dataset_job_stages
            self.assertEqual(len(dataset_job_stagees), 2)


class BatchesApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test_project')
            session.add(project)
            session.flush([project])

            dataset = Dataset(name='test_dataset',
                              dataset_type=DatasetType.PSI,
                              uuid=resource_uuid(),
                              comment='comment',
                              path='/data/dataset/321',
                              project_id=project.id,
                              dataset_format=DatasetFormat.TABULAR.value,
                              dataset_kind=DatasetKindV2.RAW)
            session.add(dataset)

            data_source = DataSource(name='test_datasource',
                                     uuid=resource_uuid(),
                                     path='/upload/',
                                     project_id=project.id,
                                     dataset_kind=DatasetKindV2.SOURCE)
            session.add(data_source)

            session.commit()
            self._project_id = project.id
            self._dataset_id = dataset.id
            self._data_source_id = data_source.id
            self._data_source_uuid = data_source.uuid

    def test_get_data_batches(self):
        with db.session_scope() as session:
            data_batch_1 = DataBatch(dataset_id=self._dataset_id,
                                     name='20220101',
                                     event_time=datetime(2022, 1, 1),
                                     created_at=datetime(2022, 1, 1, 0, 0, 0),
                                     comment='batch_1',
                                     path='/data/dataset/123/batch/20220101')
            session.add(data_batch_1)
            data_batch_2 = DataBatch(dataset_id=self._dataset_id,
                                     name='20220102',
                                     event_time=datetime(2022, 1, 2),
                                     created_at=datetime(2022, 1, 2, 0, 0, 0),
                                     comment='batch_2',
                                     path='/data/dataset/123/batch/20220102')
            session.add(data_batch_2)
            session.commit()
        sorter_param = urllib.parse.quote('created_at asc')
        response = self.get_helper(
            f'/api/v2/datasets/{self._dataset_id}/batches?page=1&page_size=5&order_by={sorter_param}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            response,
            [{
                'id': 1,
                'dataset_id': 1,
                'comment': 'batch_1',
                'created_at': to_timestamp(datetime(2022, 1, 1, 0, 0, 0)),
                'event_time': to_timestamp(datetime(2022, 1, 1)),
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'name': '20220101',
                'path': '/data/dataset/123/batch/20220101',
                'state': 'FAILED',
                'latest_parent_dataset_job_stage_id': 0,
                'latest_analyzer_dataset_job_stage_id': 0,
            }, {
                'id': 2,
                'dataset_id': 1,
                'comment': 'batch_2',
                'created_at': to_timestamp(datetime(2022, 1, 2, 0, 0, 0)),
                'event_time': to_timestamp(datetime(2022, 1, 2)),
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'name': '20220102',
                'path': '/data/dataset/123/batch/20220102',
                'state': 'FAILED',
                'latest_parent_dataset_job_stage_id': 0,
                'latest_analyzer_dataset_job_stage_id': 0,
            }],
            ignore_fields=['updated_at'],
        )
        self.assertEqual(
            json.loads(response.data).get('page_meta'), {
                'current_page': 1,
                'page_size': 5,
                'total_pages': 1,
                'total_items': 2
            })


class BatchApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(name='test_project')
            session.add(project)
            session.flush([project])

            dataset = Dataset(name='test_dataset',
                              dataset_type=DatasetType.STREAMING,
                              uuid=resource_uuid(),
                              comment='comment',
                              path='/data/dataset/123',
                              project_id=project.id,
                              dataset_format=DatasetFormat.TABULAR.value,
                              dataset_kind=DatasetKindV2.RAW)
            session.add(dataset)
            session.flush()

            data_batch = DataBatch(dataset_id=dataset.id,
                                   name='20220101',
                                   event_time=datetime(2022, 1, 1),
                                   created_at=datetime(2022, 1, 1, 0, 0, 0),
                                   comment='batch_1',
                                   path='/data/dataset/123/batch/20220101')
            session.add(data_batch)
            session.flush()

            session.commit()
            self._project_id = project.id
            self._dataset_id = dataset.id
            self._data_batch_id = data_batch.id

    def test_get_data_batch(self):
        response = self.get_helper(f'/api/v2/datasets/{self._dataset_id}/batches/{self._data_batch_id}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            response,
            {
                'id': self._data_batch_id,
                'dataset_id': self._dataset_id,
                'comment': 'batch_1',
                'created_at': to_timestamp(datetime(2022, 1, 1, 0, 0, 0)),
                'event_time': to_timestamp(datetime(2022, 1, 1)),
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'name': '20220101',
                'path': '/data/dataset/123/batch/20220101',
                'state': 'FAILED',
                'latest_parent_dataset_job_stage_id': 0,
                'latest_analyzer_dataset_job_stage_id': 0,
            },
            ignore_fields=['updated_at'],
        )


class BatchMetricsApiTest(BaseTestCase):

    def test_get_batch_metrics(self):
        with db.session_scope() as session:
            default_dataset = Dataset(id=1,
                                      name='dataset',
                                      creator_username='test',
                                      dataset_type=DatasetType.STREAMING,
                                      comment='test comment',
                                      path=os.path.join(tempfile.gettempdir(), 'dataset/123'),
                                      project_id=1,
                                      dataset_kind=DatasetKindV2.PROCESSED,
                                      dataset_format=DatasetFormat.TABULAR.value,
                                      created_at=datetime(2012, 1, 14, 12, 0, 6))
            session.add(default_dataset)
            default_databatch = DataBatch(name='20220101',
                                          id=111,
                                          event_time=datetime(2022, 1, 1),
                                          comment='comment',
                                          state=BatchState.NEW,
                                          dataset_id=1,
                                          path='/data/test/batch/20220101')
            session.add(default_databatch)
            session.commit()
        meta_file = DatasetDirectory(dataset_path=default_dataset.path).batch_meta_file(batch_name='20220101')
        gfile.makedirs(meta_file.split('/_META')[0])
        meta_data = {
            'dtypes': [{
                'key': 'f01',
                'value': 'bigint'
            }],
            'sample': [
                [
                    1,
                ],
                [
                    0,
                ],
            ],
            'count': 0,
            'features': {
                'f01': {
                    'count': '2',
                    'mean': '0.0015716767309123998',
                    'stddev': '0.03961485047808605',
                    'min': '0',
                    'max': '1',
                    'missing_count': '0'
                },
            },
            'hist': {
                'f01': {
                    'x': [
                        0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9,
                        1
                    ],
                    'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
                },
            },
        }
        with gfile.GFile(meta_file, 'w') as f:
            f.write(json.dumps(meta_data))

        feat_name = 'f01'
        feature_response = self.get_helper(f'/api/v2/datasets/1/batches/111/feature_metrics?name={feat_name}')
        self.assertEqual(feature_response.status_code, 200)
        feature_data = self.get_response_data(feature_response)
        golden_feature = {
            'name': feat_name,
            'metrics': {
                'count': '2',
                'mean': '0.0015716767309123998',
                'stddev': '0.03961485047808605',
                'min': '0',
                'max': '1',
                'missing_count': '0'
            },
            'hist': {
                'x': [
                    0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1
                ],
                'y': [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
            },
        }
        self.assertEqual(feature_data, golden_feature, 'should has feature data')


class BatchesAnalyzeApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.dataset.apis.get_pure_domain_name', lambda _: 'test_domain')
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobService.create_as_coordinator')
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobStageService.create_dataset_job_stage_as_coordinator')
    def test_analyze_data_batch(self, create_dataset_job_stage_as_coordinator: MagicMock,
                                mock_create_as_coordinator: MagicMock):
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            session.add(project)
            dataset = Dataset(id=1,
                              name='default dataset',
                              uuid='dataset_uuid',
                              creator_username='test',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment2',
                              path='data/dataset/123',
                              project_id=1,
                              dataset_kind=DatasetKindV2.PROCESSED,
                              dataset_format=DatasetFormat.TABULAR.value)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220101',
                                   comment='comment',
                                   event_time=datetime(2022, 1, 1),
                                   dataset_id=1,
                                   path='/data/dataset/123/batch/20220101')
            session.add(data_batch)
            session.commit()
        mock_dataset_job = DatasetJob(id=1,
                                      name='analyzer_dataset_job',
                                      uuid='123',
                                      project_id=1,
                                      output_dataset_id=1,
                                      input_dataset_id=1,
                                      kind=DatasetJobKind.ANALYZER,
                                      coordinator_id=0,
                                      state=DatasetJobState.PENDING,
                                      created_at=datetime(2022, 1, 1),
                                      updated_at=datetime(2022, 1, 1),
                                      creator_username='test user')
        mock_dataset_job.set_global_configs(global_configs=dataset_pb2.DatasetJobGlobalConfigs(
            global_configs={
                'test_domain':
                    dataset_pb2.DatasetJobConfig(dataset_uuid='u123',
                                                 variables=[
                                                     Variable(name='name1', value='value1'),
                                                     Variable(name='name2', value='value2'),
                                                     Variable(name='name3', value='value3')
                                                 ])
            }))
        mock_create_as_coordinator.return_value = mock_dataset_job
        response = self.post_helper(
            '/api/v2/datasets/1/batches/1:analyze', {
                'dataset_job_config': {
                    'variables': [{
                        'name': 'name1',
                        'value': 'value1',
                    }, {
                        'name': 'name2',
                        'value': 'value2',
                    }, {
                        'name': 'name3',
                        'value': 'value3',
                    }]
                }
            })
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.maxDiff = None
        self.assertResponseDataEqual(
            response, {
                'name': 'analyzer_dataset_job',
                'uuid': '123',
                'project_id': 1,
                'kind': 'ANALYZER',
                'state': 'PENDING',
                'created_at': to_timestamp(datetime(2022, 1, 1)),
                'updated_at': to_timestamp(datetime(2022, 1, 1)),
                'result_dataset_uuid': '',
                'result_dataset_name': '',
                'is_ready': False,
                'input_data_batch_num_example': 0,
                'output_data_batch_num_example': 0,
                'id': 1,
                'coordinator_id': 0,
                'workflow_id': 0,
                'finished_at': 0,
                'started_at': 0,
                'has_stages': False,
                'creator_username': 'test user',
                'scheduler_state': '',
                'global_configs': ANY,
                'time_range': {
                    'days': 0,
                    'hours': 0,
                },
                'scheduler_message': '',
            })
        create_dataset_job_stage_as_coordinator.assert_called_once_with(
            project_id=1,
            dataset_job_id=1,
            output_data_batch_id=1,
            global_configs=dataset_pb2.DatasetJobGlobalConfigs(
                global_configs={
                    'test_domain':
                        dataset_pb2.DatasetJobConfig(dataset_uuid='u123',
                                                     variables=[
                                                         Variable(name='name1', value='value1'),
                                                         Variable(name='name2', value='value2'),
                                                         Variable(name='name3', value='value3')
                                                     ])
                }))


class BatchRerunApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.dataset.apis.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobStageService.create_dataset_job_stage_as_coordinator')
    def test_rerun_batch(self, mock_create_dataset_job_stage_as_coordinator: MagicMock, mock_list_flags: MagicMock):
        with db.session_scope() as session:
            project = Project(id=1, name='test-project')
            session.add(project)
            dataset = Dataset(id=1,
                              name='default dataset',
                              uuid='dataset_uuid',
                              creator_username='test',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment2',
                              path='data/dataset/123',
                              project_id=1,
                              dataset_kind=DatasetKindV2.PROCESSED,
                              dataset_format=DatasetFormat.TABULAR.value)
            session.add(dataset)
            data_batch = DataBatch(id=1,
                                   name='20220101',
                                   comment='comment',
                                   event_time=datetime(2022, 1, 1),
                                   dataset_id=1,
                                   path='/data/dataset/123/batch/20220101')
            session.add(data_batch)
            dataset_job = DatasetJob(id=1,
                                     name='default dataset_job',
                                     uuid='u123',
                                     project_id=1,
                                     output_dataset_id=1,
                                     input_dataset_id=1,
                                     kind=DatasetJobKind.OT_PSI_DATA_JOIN,
                                     coordinator_id=0,
                                     state=DatasetJobState.PENDING,
                                     created_at=datetime(2022, 1, 1),
                                     updated_at=datetime(2022, 1, 1),
                                     creator_username='test user')
            dataset_job.set_global_configs(global_configs=dataset_pb2.DatasetJobGlobalConfigs(
                global_configs={
                    'coordinator_domain':
                        dataset_pb2.DatasetJobConfig(dataset_uuid='u123',
                                                     variables=[
                                                         Variable(name='name1',
                                                                  typed_value=Value(string_value='value1-1'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name2',
                                                                  typed_value=Value(string_value='value1-2'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name3',
                                                                  typed_value=Value(string_value='value1-3'),
                                                                  value_type=Variable.ValueType.STRING),
                                                     ]),
                    'participant_domain':
                        dataset_pb2.DatasetJobConfig(dataset_uuid='u123',
                                                     variables=[
                                                         Variable(name='name1',
                                                                  typed_value=Value(string_value='value1-1'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name2',
                                                                  typed_value=Value(string_value='value1-2'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name3',
                                                                  typed_value=Value(string_value='value1-3'),
                                                                  value_type=Variable.ValueType.STRING),
                                                     ]),
                }))
            session.add(dataset_job)
            participant = Participant(id=1, name='participant_1', domain_name='fl-fake_domain_name_1.com')
            session.add(participant)
            session.commit()

        mock_create_dataset_job_stage_as_coordinator.return_value = DatasetJobStage(id=1,
                                                                                    name='mock stage',
                                                                                    uuid='fake stage uuid',
                                                                                    state=DatasetJobState.PENDING,
                                                                                    dataset_job_id=1,
                                                                                    data_batch_id=1,
                                                                                    coordinator_id=1,
                                                                                    created_at=datetime(2022, 1, 1),
                                                                                    updated_at=datetime(2022, 1, 1))
        rerun_config = {
            'dataset_job_parameter': {
                'global_configs': {
                    'fl-coordinator_domain.com': {
                        'variables': [{
                            'name': 'name1',
                            'typed_value': 'value2-1',
                            'value_type': 'STRING',
                        }, {
                            'name': 'name2',
                            'typed_value': 'value2-2',
                            'value_type': 'STRING',
                        }, {
                            'name': 'name3',
                            'typed_value': 'value2-3',
                            'value_type': 'STRING',
                        }]
                    },
                    'fl-participant_domain.com': {
                        'variables': [{
                            'name': 'name1',
                            'typed_value': 'value2-1',
                            'value_type': 'STRING',
                        }]
                    },
                },
            },
        }
        response = self.post_helper('/api/v2/datasets/1/batches/1:rerun', rerun_config)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_create_dataset_job_stage_as_coordinator.assert_called_once_with(
            project_id=1,
            dataset_job_id=1,
            output_data_batch_id=1,
            global_configs=dataset_pb2.DatasetJobGlobalConfigs(
                global_configs={
                    'coordinator_domain':
                        dataset_pb2.DatasetJobConfig(dataset_uuid='u123',
                                                     variables=[
                                                         Variable(name='name1',
                                                                  typed_value=Value(string_value='value2-1'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name2',
                                                                  typed_value=Value(string_value='value2-2'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name3',
                                                                  typed_value=Value(string_value='value2-3'),
                                                                  value_type=Variable.ValueType.STRING),
                                                     ]),
                    'participant_domain':
                        dataset_pb2.DatasetJobConfig(dataset_uuid='u123',
                                                     variables=[
                                                         Variable(name='name1',
                                                                  typed_value=Value(string_value='value2-1'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name2',
                                                                  typed_value=Value(string_value='value1-2'),
                                                                  value_type=Variable.ValueType.STRING),
                                                         Variable(name='name3',
                                                                  typed_value=Value(string_value='value1-3'),
                                                                  value_type=Variable.ValueType.STRING),
                                                     ]),
                }))

        # test participant not support rerun
        mock_list_flags.return_value = {'data_batch_rerun_enabled': False}
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            dataset_job.coordinator_id = 1
            session.commit()
        response = self.post_helper('/api/v2/datasets/1/batches/1:rerun', rerun_config)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class DataSourcesApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            default_project = Project(id=1, name='default_project')
            datasource_1 = DataSource(id=100,
                                      uuid=resource_uuid(),
                                      name='datasource_1',
                                      creator_username='test',
                                      path='hdfs:///data/fake_path_1',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 5),
                                      is_published=False,
                                      store_format=StoreFormat.TFRECORDS,
                                      dataset_format=DatasetFormat.IMAGE.value,
                                      dataset_type=DatasetType.STREAMING)
            datasource_1.set_meta_info(meta=dataset_pb2.DatasetMetaInfo(datasource_type=DataSourceType.HDFS.value))
            datasource_2 = DataSource(id=101,
                                      uuid=resource_uuid(),
                                      name='datasource_2',
                                      creator_username='test',
                                      path='hdfs:///data/fake_path_2',
                                      project_id=1,
                                      created_at=datetime(2012, 1, 14, 12, 0, 6),
                                      is_published=False,
                                      store_format=StoreFormat.CSV,
                                      dataset_format=DatasetFormat.TABULAR.value,
                                      dataset_type=DatasetType.PSI)
            datasource_2.set_meta_info(meta=dataset_pb2.DatasetMetaInfo(datasource_type=DataSourceType.HDFS.value))
            session.add(default_project)
            session.add(datasource_1)
            session.add(datasource_2)
            session.commit()

    def test_parse_data_source_url(self):
        url = 'hdfs:///home/test'
        data_source = dataset_pb2.DataSource(type=DataSourceType.HDFS.value,
                                             url='hdfs:///home/test',
                                             is_user_upload=False)
        self.assertEqual(_parse_data_source_url(url), data_source)

        url = '/data/test'
        data_source = dataset_pb2.DataSource(type=DataSourceType.FILE.value,
                                             url='file:///data/test',
                                             is_user_upload=False)
        self.assertEqual(_parse_data_source_url(url), data_source)

        url = '/data/test'
        data_source = dataset_pb2.DataSource(type=DataSourceType.FILE.value,
                                             url='file:///data/test',
                                             is_user_upload=False)
        self.assertEqual(_parse_data_source_url(url), data_source)
        url = 'hdfs/'
        with self.assertRaises(ValidationError):
            _parse_data_source_url(url)

    @patch('fedlearner_webconsole.utils.file_manager.FileManager.listdir')
    @patch('fedlearner_webconsole.utils.file_manager.FileManager.isdir', fake_isdir)
    @patch('fedlearner_webconsole.dataset.apis.Envs.STORAGE_ROOT', new_callable=PropertyMock)
    def test_data_source_check_connection(self, mock_storage_root: MagicMock, mock_listdir: MagicMock):
        mock_storage_root.return_value = 'hdfs:///home/'
        mock_listdir.return_value = ['_SUCCESS', 'test.csv']
        resp = self.post_helper('/api/v2/data_sources:check_connection', {
            'data_source_url': 'hdfs:///home/',
            'file_num': 1,
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {
            'file_names': ['_SUCCESS',],
            'extra_nums': 1,
        })

        mock_storage_root.reset_mock()
        mock_storage_root.return_value = 'file:///data'
        resp = self.post_helper('/api/v2/data_sources:check_connection', {'data_source_url': 'file:///data/test'})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {
            'file_names': ['_SUCCESS', 'test.csv'],
            'extra_nums': 0,
        })

        resp = self.post_helper('/api/v2/data_sources:check_connection', {'data_source_url': 'file:///data/fake_path'})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        resp = self.post_helper('/api/v2/data_sources:check_connection', {})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('required', resp.json.get('details').get('json').get('data_source_url')[0])

        resp = self.post_helper('/api/v2/data_sources:check_connection', {'data_source_url': 'hdfs:/home/'})
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(resp.json.get('details'), 'invalid data_source_url: hdfs:/home/')

        mock_listdir.reset_mock()
        mock_listdir.return_value = ['20220801', '20220802']
        resp = self.post_helper('/api/v2/data_sources:check_connection', {
            'data_source_url': 'hdfs:///home/',
            'dataset_type': 'STREAMING'
        })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(resp, {
            'file_names': ['20220801', '20220802'],
            'extra_nums': 0,
        })

        mock_listdir.reset_mock()
        mock_listdir.return_value = ['20220803-15', '2022080316']
        resp = self.post_helper('/api/v2/data_sources:check_connection', {
            'data_source_url': 'hdfs:///home/',
            'dataset_type': 'STREAMING'
        })
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(resp.json.get('details'), 'illegal dir format: 2022080316')

    @patch('fedlearner_webconsole.dataset.apis.Envs.STORAGE_ROOT', '2022080316')
    @patch('fedlearner_webconsole.dataset.apis._validate_data_source', lambda *args: None)
    def test_post_data_source(self):
        resp = self.post_helper(
            '/api/v2/data_sources', {
                'data_source': {
                    'name': 'test',
                    'comment': 'test comment',
                    'data_source_url': 'hdfs:///home/fake_path',
                },
                'project_id': 1
            })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        self.assertResponseDataEqual(resp, {
            'type': DataSourceType.HDFS.value,
            'url': 'hdfs:///home/fake_path',
            'name': 'test',
            'creator_username': 'ada',
            'project_id': 1,
            'is_user_upload': False,
            'is_user_export': False,
            'dataset_format': 'TABULAR',
            'store_format': 'UNKNOWN',
            'dataset_type': 'PSI',
            'comment': 'test comment',
        },
                                     ignore_fields=['created_at', 'id', 'uuid'])

        resp_upload = self.post_helper('/api/v2/data_sources', {
            'data_source': {
                'name': 'test',
                'data_source_url': '/home/fake_path',
                'is_user_upload': True,
            },
            'project_id': 1
        })
        self.assertEqual(resp_upload.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            resp_upload.json.get('details'),
            {'json': {
                'data_source': {
                    'data_source_url': ['no access to unauchority path file:///home/fake_path!']
                }
            }})

        resp_upload_hdfs = self.post_helper(
            '/api/v2/data_sources', {
                'data_source': {
                    'name': 'test',
                    'data_source_url': 'hdfs:///home/fake_path',
                    'is_user_upload': True,
                    'dataset_format': 'TABULAR',
                    'store_format': 'TFRECORDS',
                    'dataset_type': 'STREAMING',
                },
                'project_id': 1
            })
        self.assertEqual(resp_upload_hdfs.status_code, HTTPStatus.CREATED)
        self.assertResponseDataEqual(resp_upload_hdfs, {
            'type': DataSourceType.HDFS.value,
            'url': 'hdfs:///home/fake_path',
            'name': 'test',
            'creator_username': 'ada',
            'project_id': 1,
            'is_user_upload': True,
            'is_user_export': False,
            'dataset_format': 'TABULAR',
            'store_format': 'TFRECORDS',
            'dataset_type': 'STREAMING',
            'comment': '',
        },
                                     ignore_fields=['created_at', 'id', 'uuid'])

        resp_err = self.post_helper('/api/v2/data_sources', {
            'data_source': {
                'name': 'test',
                'data_source_url': 'fake:///home/fake_path',
            },
            'project_id': 1
        })
        self.assertEqual(resp_err.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(resp_err.json.get('details'),
                         {'json': {
                             'data_source': {
                                 'data_source_url': ['fake is not a supported data_source type']
                             }
                         }})

    def test_delete_data_source(self):
        resp = self.delete_helper('/api/v2/data_sources/100')
        self.assertEqual(resp.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            dataset = session.query(DataSource).get(100)
            self.assertIsNone(dataset)

    def test_get_data_sources(self):
        expected_result = [{
            'id': 101,
            'uuid': ANY,
            'name': 'datasource_2',
            'comment': '',
            'creator_username': 'test',
            'url': 'hdfs:///data/fake_path_2',
            'type': DataSourceType.HDFS.value,
            'project_id': 1,
            'created_at': to_timestamp(datetime(2012, 1, 14, 12, 0, 6)),
            'is_user_upload': False,
            'is_user_export': False,
            'dataset_format': 'TABULAR',
            'store_format': 'CSV',
            'dataset_type': 'PSI',
        }, {
            'id': 100,
            'uuid': ANY,
            'name': 'datasource_1',
            'comment': '',
            'creator_username': 'test',
            'url': 'hdfs:///data/fake_path_1',
            'type': DataSourceType.HDFS.value,
            'project_id': 1,
            'created_at': to_timestamp(datetime(2012, 1, 14, 12, 0, 5)),
            'is_user_upload': False,
            'is_user_export': False,
            'dataset_format': 'IMAGE',
            'store_format': 'TFRECORDS',
            'dataset_type': 'STREAMING',
        }]
        resp = self.get_helper('/api/v2/data_sources')
        self.assertResponseDataEqual(resp, expected_result)

        resp = self.get_helper('/api/v2/data_sources?project_id=1')
        self.assertResponseDataEqual(resp, expected_result)

        resp = self.get_helper('/api/v2/data_sources?project_id=10')
        self.assertResponseDataEqual(resp, [])

    def test_get_data_source(self):
        resp = self.get_helper('/api/v2/data_sources/100')
        self.assertEqual(resp.status_code, 200)
        self.assertResponseDataEqual(
            resp, {
                'id': 100,
                'uuid': ANY,
                'name': 'datasource_1',
                'comment': '',
                'creator_username': 'test',
                'url': 'hdfs:///data/fake_path_1',
                'type': DataSourceType.HDFS.value,
                'project_id': 1,
                'created_at': to_timestamp(datetime(2012, 1, 14, 12, 0, 5)),
                'is_user_upload': False,
                'is_user_export': False,
                'dataset_format': 'IMAGE',
                'store_format': 'TFRECORDS',
                'dataset_type': 'STREAMING',
            })
        resp = self.get_helper('/api/v2/data_sources/1')
        self.assertEqual(resp.status_code, 404)

    @patch('fedlearner_webconsole.dataset.apis.Envs.STORAGE_ROOT', '/data')
    def test_path_authority_validator(self):
        _path_authority_validator('/data/test')
        _path_authority_validator('hdfs:///home')
        _path_authority_validator('file:///data/test')
        with self.assertRaises(ValidationError):
            _path_authority_validator('fake')
        with self.assertRaises(ValidationError):
            _path_authority_validator('/fake')
        with self.assertRaises(ValidationError):
            _path_authority_validator('file:///fake')


class DataSourceTreeApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.utils.file_tree.FileTreeBuilder.build_with_root')
    def test_get_tree(self, mock_build_with_root: MagicMock):
        mock_build_with_root.return_value = FileTreeNode(filename='20221101',
                                                         path='20221101',
                                                         is_directory=True,
                                                         size=1024,
                                                         mtime=0,
                                                         files=[
                                                             FileTreeNode(filename='test.csv',
                                                                          path='20221101/test.csv',
                                                                          is_directory=False,
                                                                          size=1024,
                                                                          mtime=0),
                                                         ])
        with db.session_scope() as session:
            data_source = DataSource(id=100,
                                     uuid=resource_uuid(),
                                     name='datasource_1',
                                     creator_username='test',
                                     path='hdfs:///data/fake_path_1',
                                     project_id=1,
                                     created_at=datetime(2012, 1, 14, 12, 0, 5),
                                     is_published=False,
                                     store_format=StoreFormat.TFRECORDS,
                                     dataset_format=DatasetFormat.IMAGE.value,
                                     dataset_type=DatasetType.STREAMING)
            session.add(data_source)
            session.commit()
        resp = self.get_helper('/api/v2/data_sources/100/tree')
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            resp, {
                'filename':
                    '20221101',
                'path':
                    '20221101',
                'is_directory':
                    True,
                'size':
                    1024,
                'mtime':
                    0,
                'files': [{
                    'filename': 'test.csv',
                    'path': '20221101/test.csv',
                    'is_directory': False,
                    'size': 1024,
                    'mtime': 0,
                    'files': [],
                }],
            })


class ParticipantDatasetApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            project = Project(id=10, name='test-project')
            participant_1 = Participant(id=10, name='participant_1', domain_name='fake_domain_name_1')
            project_participant_1 = ProjectParticipant(project_id=project.id, participant_id=participant_1.id)

            session.add(project)
            session.add(participant_1)
            session.add(project_participant_1)
            session.commit()

    @patch('fedlearner_webconsole.dataset.apis.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.rpc.v2.resource_service_client.ResourceServiceClient.list_datasets')
    @patch('fedlearner_webconsole.rpc.client.RpcClient.list_participant_datasets')
    def test_get_paricipant(self, mock_list_participant_datasets: MagicMock, mock_list_datasets: MagicMock,
                            mock_list_flags: MagicMock):
        dataref_1 = dataset_pb2.ParticipantDatasetRef(uuid='1',
                                                      name='fake_dataset_1',
                                                      format=DatasetFormat.TABULAR.name,
                                                      file_size=1000,
                                                      dataset_kind=DatasetKindV2.RAW.name,
                                                      dataset_type=DatasetType.PSI.name,
                                                      auth_status='PENDING')
        dataref_2 = dataset_pb2.ParticipantDatasetRef(uuid='2',
                                                      name='fake_dataset_2',
                                                      format=DatasetFormat.TABULAR.name,
                                                      file_size=1000,
                                                      dataset_kind=DatasetKindV2.PROCESSED.name,
                                                      dataset_type=DatasetType.PSI.name,
                                                      auth_status='PENDING')
        mock_return = service_pb2.ListParticipantDatasetsResponse(participant_datasets=[dataref_1, dataref_2])
        mock_list_participant_datasets.return_value = mock_return
        mock_list_flags.return_value = {'list_datasets_rpc_enabled': False}

        # test no filter
        resp = self.get_helper('/api/v2/project/10/participant_datasets')
        self.assertEqual(resp.status_code, 200)
        expect_data = [{
            'uuid': '1',
            'project_id': 10,
            'name': 'fake_dataset_1',
            'participant_id': 10,
            'format': DatasetFormat.TABULAR.name,
            'file_size': 1000,
            'updated_at': 0,
            'value': 0,
            'dataset_kind': 'RAW',
            'dataset_type': 'PSI',
            'auth_status': 'PENDING',
        }, {
            'uuid': '2',
            'project_id': 10,
            'name': 'fake_dataset_2',
            'participant_id': 10,
            'format': DatasetFormat.TABULAR.name,
            'file_size': 1000,
            'updated_at': 0,
            'value': 0,
            'dataset_kind': 'PROCESSED',
            'dataset_type': 'PSI',
            'auth_status': 'PENDING',
        }]
        resp_data = self.get_response_data(resp)
        self.assertCountEqual(resp_data, expect_data)
        mock_list_participant_datasets.assert_called_once_with(kind=None, uuid=None)
        mock_list_datasets.assert_not_called()
        mock_list_participant_datasets.reset_mock()

        # test filter uuid
        mock_list_participant_datasets.return_value = mock_return
        resp = self.get_helper('/api/v2/project/10/participant_datasets?uuid=1')
        self.assertEqual(resp.status_code, 200)
        expect_data = [{
            'uuid': '1',
            'project_id': 10,
            'name': 'fake_dataset_1',
            'participant_id': 10,
            'format': DatasetFormat.TABULAR.name,
            'file_size': 1000,
            'updated_at': 0,
            'value': 0,
            'dataset_kind': 'RAW',
            'dataset_type': 'PSI',
            'auth_status': 'PENDING',
        }]
        self.assertResponseDataEqual(resp, expect_data)
        mock_list_participant_datasets.assert_called_once_with(kind=None, uuid='1')
        mock_list_participant_datasets.reset_mock()

        # test illegal kind
        mock_list_participant_datasets.return_value = service_pb2.ListParticipantDatasetsResponse()
        resp = self.get_helper('/api/v2/project/10/participant_datasets?kind=unkown')
        self.assertEqual(resp.status_code, 400)
        mock_list_participant_datasets.assert_not_called()

        # test filter kind
        resp = self.get_helper('/api/v2/project/10/participant_datasets?kind=raw')
        self.assertEqual(resp.status_code, 200)
        mock_list_participant_datasets.assert_called_once_with(kind='raw', uuid=None)

        # test filter participant_id
        mock_list_participant_datasets.reset_mock()
        mock_list_participant_datasets.return_value = mock_return
        resp = self.get_helper('/api/v2/project/10/participant_datasets?participant_id=10')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.get_response_data(resp)), 2)
        mock_list_participant_datasets.assert_called_once_with(kind=None, uuid=None)

        # test filter participant_id not found
        mock_list_participant_datasets.reset_mock()
        mock_list_participant_datasets.return_value = mock_return
        resp = self.get_helper('/api/v2/project/10/participant_datasets?participant_id=100')
        self.assertEqual(resp.status_code, 404)
        mock_list_participant_datasets.assert_not_called()

        # test list_datasets_rpc
        mock_list_participant_datasets.reset_mock()
        mock_list_datasets.reset_mock()
        mock_list_flags.reset_mock()

        mock_list_datasets.return_value = mock_return
        mock_list_flags.return_value = {'list_datasets_rpc_enabled': True}
        resp = self.get_helper('/api/v2/project/10/participant_datasets?uuid=1&kind=raw')
        self.assertEqual(resp.status_code, 200)
        self.assertResponseDataEqual(resp, expect_data)
        mock_list_datasets.assert_called_once_with(kind=DatasetKindV2.RAW,
                                                   uuid='1',
                                                   state=ResourceState.SUCCEEDED,
                                                   time_range=None)
        mock_list_participant_datasets.assert_not_called()

        # test filter cron
        mock_list_datasets.reset_mock()
        mock_list_datasets.return_value = mock_return
        resp = self.get_helper('/api/v2/project/10/participant_datasets?cron_interval=DAYS')
        self.assertEqual(resp.status_code, 200)
        mock_list_datasets.assert_called_once_with(kind=None,
                                                   uuid=None,
                                                   state=ResourceState.SUCCEEDED,
                                                   time_range=dataset_pb2.TimeRange(days=1))


class PublishDatasetApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def test_publish_dataset(self):
        with db.session_scope() as session:
            published_dataset = Dataset(id=10,
                                        uuid='uuid',
                                        name='published_dataset',
                                        creator_username='test',
                                        dataset_type=DatasetType.STREAMING,
                                        comment='test comment',
                                        path='/data/dataset/123',
                                        is_published=False,
                                        project_id=1,
                                        dataset_format=DatasetFormat.TABULAR.value,
                                        created_at=datetime(2022, 1, 1, 12, 0, 0),
                                        updated_at=datetime(2022, 1, 1, 12, 0, 0))
            session.add(published_dataset)
            dataset_job = DatasetJob(workflow_id=0,
                                     uuid=resource_uuid(),
                                     project_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            session.commit()
        resp = self.post_helper('/api/v2/datasets/10:publish', {})
        self.assertEqual(resp.status_code, 200)
        self.assertResponseDataEqual(
            resp,
            {
                'id': 10,
                'uuid': 'uuid',
                'is_published': True,
                'name': 'published_dataset',
                'creator_username': 'test',
                'path': '/data/dataset/123',
                'comment': 'test comment',
                'project_id': 1,
                'dataset_kind': 'RAW',
                'dataset_format': 'TABULAR',
                'file_size': 0,
                'num_example': 0,
                'num_feature': 0,
                'state_frontend': 'SUCCEEDED',
                'parent_dataset_job_id': 1,
                'workflow_id': 0,
                'value': 0,
                'schema_checkers': [],
                'dataset_type': 'STREAMING',
                'import_type': 'COPY',
                'store_format': 'TFRECORDS',
                'analyzer_dataset_job_id': 0,
                'publish_frontend_state': 'PUBLISHED',
                'auth_frontend_state': 'AUTH_APPROVED',
                'local_auth_status': 'PENDING',
                'participants_info': {
                    'participants_map': {}
                },
            },
            ignore_fields=['created_at', 'updated_at', 'deleted_at', 'data_source'],
        )

    @patch('fedlearner_webconsole.dataset.services.DatasetService.withdraw_dataset')
    def test_revoke_published_dataset(self, fake_withdraw_dataset: MagicMock):
        resp = self.delete_helper('/api/v2/datasets/11:publish')
        self.assertEqual(resp.status_code, 204)
        fake_withdraw_dataset.assert_called_once_with(11)


class DatasetAuthorizehApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()

        with db.session_scope() as session:
            dataset = Dataset(id=10,
                              uuid='uuid',
                              name='default dataset',
                              creator_username='test',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment',
                              path='/data/dataset/123',
                              is_published=False,
                              project_id=1,
                              dataset_format=DatasetFormat.TABULAR.value,
                              auth_status=AuthStatus.PENDING)
            dataset.set_participants_info(participants_info=ParticipantsInfo(
                participants_map={'test_domain': ParticipantInfo(auth_status='PENDING')}))
            session.add(dataset)
            dataset_job = DatasetJob(workflow_id=0,
                                     uuid=resource_uuid(),
                                     project_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            session.commit()

    @patch('fedlearner_webconsole.dataset.apis.SettingService.get_system_info',
           lambda: setting_pb2.SystemInfo(pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobController.inform_auth_status')
    def test_authorize_dataset(self, mock_inform_auth_status: MagicMock):
        resp = self.post_helper('/api/v2/datasets/10:authorize')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.get_response_data(resp).get('local_auth_status'), 'AUTHORIZED')
        self.assertEqual(
            self.get_response_data(resp).get('participants_info'), {
                'participants_map': {
                    'test_domain': {
                        'auth_status': 'AUTHORIZED',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': '',
                    }
                }
            })
        mock_inform_auth_status.assert_called_once_with(dataset_job=ANY, auth_status=AuthStatus.AUTHORIZED)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.auth_status, AuthStatus.AUTHORIZED)
            self.assertEqual(
                dataset.get_participants_info(),
                ParticipantsInfo(participants_map={'test_domain': ParticipantInfo(auth_status='AUTHORIZED')}))

    @patch('fedlearner_webconsole.dataset.apis.SettingService.get_system_info',
           lambda: setting_pb2.SystemInfo(pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobController.inform_auth_status')
    def test_revoke_authorized_dataset(self, mock_inform_auth_status: MagicMock):
        resp = self.delete_helper('/api/v2/datasets/10:authorize')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.get_response_data(resp).get('local_auth_status'), 'WITHDRAW')
        self.assertEqual(
            self.get_response_data(resp).get('participants_info'), {
                'participants_map': {
                    'test_domain': {
                        'auth_status': 'WITHDRAW',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': '',
                    }
                }
            })
        mock_inform_auth_status.assert_called_once_with(dataset_job=ANY, auth_status=AuthStatus.WITHDRAW)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.auth_status, AuthStatus.WITHDRAW)
            self.assertEqual(
                dataset.get_participants_info(),
                ParticipantsInfo(participants_map={'test_domain': ParticipantInfo(auth_status='WITHDRAW')}))


class DatasetFlushAuthStatusApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()

        with db.session_scope() as session:
            project = Project(id=1, name='test_project')
            session.add(project)
            dataset = Dataset(id=10,
                              uuid='uuid',
                              name='default dataset',
                              creator_username='test',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment',
                              path='/data/dataset/123',
                              is_published=False,
                              project_id=1,
                              dataset_format=DatasetFormat.TABULAR.value,
                              auth_status=AuthStatus.AUTHORIZED)
            participants_info = ParticipantsInfo(
                participants_map={
                    'coordinator-domain-name': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                    'participant-domain-name': ParticipantInfo(auth_status=AuthStatus.PENDING.name)
                })
            dataset.set_participants_info(participants_info=participants_info)
            session.add(dataset)
            dataset_job = DatasetJob(workflow_id=0,
                                     uuid=resource_uuid(),
                                     project_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            session.commit()

    @patch('fedlearner_webconsole.dataset.controllers.SystemServiceClient.list_flags')
    @patch('fedlearner_webconsole.dataset.controllers.ResourceServiceClient.list_datasets')
    @patch('fedlearner_webconsole.dataset.controllers.DatasetJobService.get_participants_need_distribute')
    def test_authorize_dataset(self, mock_get_participants_need_distribute: MagicMock, mock_list_datasets: MagicMock,
                               mock_list_flags: MagicMock):
        participant = Participant(id=1, name='test_participant', domain_name='fl-participant-domain-name.com')
        mock_get_participants_need_distribute.return_value = [participant]
        mock_list_datasets.return_value = ListDatasetsResponse(
            participant_datasets=[dataset_pb2.ParticipantDatasetRef(auth_status=AuthStatus.AUTHORIZED.name)])
        mock_list_flags.return_value = {'list_datasets_rpc_enabled': True}

        resp = self.post_helper('/api/v2/datasets/10:flush_auth_status')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            self.get_response_data(resp).get('participants_info'), {
                'participants_map': {
                    'coordinator-domain-name': {
                        'auth_status': 'AUTHORIZED',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': '',
                    },
                    'participant-domain-name': {
                        'auth_status': 'AUTHORIZED',
                        'name': '',
                        'role': '',
                        'state': '',
                        'type': '',
                    }
                }
            })
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(
                dataset.get_participants_info(),
                ParticipantsInfo(
                    participants_map={
                        'coordinator-domain-name': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                        'participant-domain-name': ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
                    }))


class DatasetStateFixApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def test_dataset_state_fix(self):
        self.signin_as_admin()
        with db.session_scope() as session:
            dataset = Dataset(id=10,
                              uuid='uuid',
                              name='dataset',
                              dataset_type=DatasetType.STREAMING,
                              comment='test comment',
                              path='/data/dataset/123',
                              is_published=False,
                              project_id=1,
                              dataset_format=DatasetFormat.TABULAR.value,
                              created_at=datetime(2022, 1, 1, 12, 0, 0),
                              updated_at=datetime(2022, 1, 1, 12, 0, 0))
            session.add(dataset)
            workflow = Workflow(id=11, state=WorkflowState.FAILED, name='fake_workflow')
            session.add(workflow)
            dataset_job = DatasetJob(workflow_id=11,
                                     uuid=resource_uuid(),
                                     project_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     input_dataset_id=1,
                                     output_dataset_id=10,
                                     state=DatasetJobState.RUNNING)
            session.add(dataset_job)

            session.commit()
        resp = self.post_helper('/api/v2/datasets/10:state_fix', {})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.parent_dataset_job.state, DatasetJobState.FAILED)

        with db.session_scope() as session:
            workflow = session.query(Workflow).get(11)
            workflow.state = WorkflowState.COMPLETED
            session.commit()
        resp = self.post_helper('/api/v2/datasets/10:state_fix', {})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.parent_dataset_job.state, DatasetJobState.RUNNING)

        resp = self.post_helper('/api/v2/datasets/10:state_fix', {'force': 'SUCCEEDED'})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            dataset = session.query(Dataset).get(10)
            self.assertEqual(dataset.parent_dataset_job.state, DatasetJobState.SUCCEEDED)


class DatasetJobsApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()

        with db.session_scope() as session:
            project = Project(name='test_project')
            session.add(project)
            session.flush([project])

            input_dataset = Dataset(id=1,
                                    uuid=resource_uuid(),
                                    is_published=False,
                                    name='input_dataset',
                                    path='/data/dataset/test_123',
                                    project_id=project.id,
                                    dataset_format=DatasetFormat.TABULAR.value,
                                    dataset_type=DatasetType.PSI,
                                    dataset_kind=DatasetKindV2.RAW)
            session.add(input_dataset)
            streaming_dataset = Dataset(id=2,
                                        uuid=resource_uuid(),
                                        is_published=False,
                                        name='streaming_dataset',
                                        path='/data/dataset/test_123',
                                        project_id=project.id,
                                        dataset_format=DatasetFormat.TABULAR.value,
                                        dataset_type=DatasetType.STREAMING,
                                        dataset_kind=DatasetKindV2.RAW)
            session.add(streaming_dataset)

            session.commit()
            self._project_id = project.id
            self._input_dataset_uuid = input_dataset.uuid

    @patch('fedlearner_webconsole.dataset.apis.DatasetJobConfiger.from_kind',
           lambda *args: FakeDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.utils.domain_name.get_pure_domain_name', lambda _: 'test_domain')
    @patch('fedlearner_webconsole.dataset.apis.SettingService.get_system_info',
           lambda: setting_pb2.SystemInfo(pure_domain_name='test_domain', domain_name='test_domain.fedlearner.net'))
    @patch('fedlearner_webconsole.dataset.services.DatasetJobService.get_participants_need_distribute')
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobService.create_as_coordinator')
    def test_post_dataset_job(self, mock_create_as_coordinator: MagicMock,
                              mock_get_participants_need_distribute: MagicMock):
        mock_get_participants_need_distribute.return_value = [
            Participant(id=1, name='test_participant_1', domain_name='fl-test-domain-name-1.com'),
            Participant(id=2, name='test_participant_2', domain_name='fl-test-domain-name-2.com')
        ]

        dataset_job = DatasetJob(uuid=resource_uuid(),
                                 project_id=1,
                                 kind=DatasetJobKind.DATA_ALIGNMENT,
                                 state=DatasetJobState.PENDING,
                                 created_at=datetime(2012, 1, 14, 12, 0, 5),
                                 updated_at=datetime(2012, 1, 14, 12, 0, 5),
                                 time_range=timedelta(days=1))
        dataset_job.input_dataset = Dataset(uuid=resource_uuid(),
                                            name='test_dataset',
                                            dataset_format=DatasetFormat.IMAGE.value)
        output_dataset = Dataset(id=2,
                                 uuid=resource_uuid(),
                                 is_published=False,
                                 name='streaming_dataset',
                                 path='/data/dataset/test_123',
                                 project_id=1,
                                 dataset_format=DatasetFormat.TABULAR.value,
                                 dataset_type=DatasetType.STREAMING,
                                 dataset_kind=DatasetKindV2.RAW,
                                 auth_status=AuthStatus.AUTHORIZED)
        property_mock = PropertyMock(return_value=output_dataset)
        DatasetJob.output_dataset = property_mock
        global_configs = dataset_pb2.DatasetJobGlobalConfigs()
        global_configs.global_configs['test'].MergeFrom(dataset_pb2.DatasetJobConfig())
        dataset_job.set_global_configs(global_configs)

        # test with error output_dataset_id
        mock_create_as_coordinator.reset_mock()
        resp = self.post_helper(
            '/api/v2/projects/1/dataset_jobs', {
                'dataset_job_parameter': {
                    'global_configs': {
                        'test_domain.fedlearner.net': {
                            'dataset_uuid': self._input_dataset_uuid,
                            'variables': []
                        },
                    },
                    'dataset_job_kind': 'RSA_PSI_DATA_JOIN',
                },
                'output_dataset_id': 100,
            })

        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        mock_create_as_coordinator.assert_not_called()

        # test cron dataset_job
        mock_create_as_coordinator.return_value = dataset_job

        resp = self.post_helper(
            '/api/v2/projects/1/dataset_jobs', {
                'dataset_job_parameter': {
                    'global_configs': {
                        'test_domain.fedlearner.net': {
                            'dataset_uuid': self._input_dataset_uuid,
                            'variables': []
                        },
                    },
                    'dataset_job_kind': 'RSA_PSI_DATA_JOIN',
                },
                'output_dataset_id': 2,
                'time_range': {
                    'days': 1,
                }
            })

        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        global_config = dataset_pb2.DatasetJobGlobalConfigs(
            global_configs={'test_domain': dataset_pb2.DatasetJobConfig(dataset_uuid=self._input_dataset_uuid)})
        mock_create_as_coordinator.assert_called_with(project_id=1,
                                                      kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                                      output_dataset_id=2,
                                                      global_configs=global_config,
                                                      time_range=timedelta(days=1))
        self.assertFalse(dataset_job.get_context().need_create_stage)

        # test non-cron dataset_job
        mock_create_as_coordinator.reset_mock()
        dataset_job.time_range = None
        mock_create_as_coordinator.return_value = dataset_job

        resp = self.post_helper(
            '/api/v2/projects/1/dataset_jobs', {
                'dataset_job_parameter': {
                    'global_configs': {
                        'test_domain.fedlearner.net': {
                            'dataset_uuid': self._input_dataset_uuid,
                            'variables': []
                        },
                    },
                    'dataset_job_kind': 'RSA_PSI_DATA_JOIN',
                },
                'output_dataset_id': 2,
                'time_range': {
                    'hours': 1,
                }
            })

        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        global_config = dataset_pb2.DatasetJobGlobalConfigs(
            global_configs={'test_domain': dataset_pb2.DatasetJobConfig(dataset_uuid=self._input_dataset_uuid)})
        mock_create_as_coordinator.assert_called_with(project_id=1,
                                                      kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                                      output_dataset_id=2,
                                                      global_configs=global_config,
                                                      time_range=timedelta(hours=1))
        self.assertEqual(
            dataset_job.output_dataset.get_participants_info(),
            ParticipantsInfo(
                participants_map={
                    'test_domain': ParticipantInfo(auth_status='AUTHORIZED'),
                    'test-domain-name-1': ParticipantInfo(auth_status='PENDING'),
                    'test-domain-name-2': ParticipantInfo(auth_status='PENDING'),
                }))
        self.assertTrue(dataset_job.get_context().need_create_stage)

    def test_get_dataset_jobs(self):
        with db.session_scope() as session:
            output_dataset_1 = Dataset(id=4,
                                       uuid=resource_uuid(),
                                       is_published=False,
                                       name='output_dataset_1',
                                       path='/data/dataset/test_123',
                                       project_id=1,
                                       dataset_format=DatasetFormat.TABULAR.value,
                                       dataset_type=DatasetType.PSI,
                                       dataset_kind=DatasetKindV2.PROCESSED)
            session.add(output_dataset_1)
            output_dataset_2 = Dataset(id=5,
                                       uuid=resource_uuid(),
                                       is_published=False,
                                       name='output_dataset_2',
                                       path='/data/dataset/test_123',
                                       project_id=2,
                                       dataset_format=DatasetFormat.TABULAR.value,
                                       dataset_type=DatasetType.PSI,
                                       dataset_kind=DatasetKindV2.PROCESSED)
            session.add(output_dataset_2)
            dataset_job_1 = DatasetJob(uuid='test-uuid-1',
                                       name='test_dataset_job_1',
                                       kind=DatasetJobKind.DATA_ALIGNMENT,
                                       project_id=1,
                                       workflow_id=1,
                                       input_dataset_id=1,
                                       output_dataset_id=4,
                                       coordinator_id=1,
                                       state=DatasetJobState.PENDING,
                                       created_at=datetime(2012, 1, 14, 12, 0, 5),
                                       creator_username='test user 1')
            session.add(dataset_job_1)

            dataset_job_2 = DatasetJob(uuid='test-uuid-2',
                                       name='test_dataset_job_2',
                                       kind=DatasetJobKind.IMPORT_SOURCE,
                                       project_id=1,
                                       workflow_id=1,
                                       input_dataset_id=2,
                                       output_dataset_id=4,
                                       coordinator_id=0,
                                       state=DatasetJobState.SUCCEEDED,
                                       created_at=datetime(2012, 1, 14, 12, 0, 6),
                                       creator_username='test user 2')
            session.add(dataset_job_2)
            dataset_job_3 = DatasetJob(uuid='test-uuid-3',
                                       name='test_dataset_job_3',
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       project_id=2,
                                       workflow_id=1,
                                       input_dataset_id=3,
                                       output_dataset_id=5,
                                       coordinator_id=0,
                                       state=DatasetJobState.PENDING,
                                       created_at=datetime(2012, 1, 14, 12, 0, 7),
                                       creator_username='test user 3')
            session.add(dataset_job_3)
            dataset_job_4 = DatasetJob(uuid='test-another-uuid-4',
                                       name='test_another_dataset_job_4',
                                       kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                       project_id=1,
                                       workflow_id=1,
                                       input_dataset_id=3,
                                       output_dataset_id=4,
                                       coordinator_id=0,
                                       state=DatasetJobState.SUCCEEDED,
                                       created_at=datetime(2012, 1, 14, 12, 0, 8),
                                       creator_username='test user 4')
            session.add(dataset_job_4)
            session.commit()

        get_response = self.get_helper('/api/v2/projects/2/dataset_jobs')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset_jobs = self.get_response_data(get_response)
        self.assertEqual(len(dataset_jobs), 1)
        self.assertEqual(dataset_jobs, [{
            'id': 3,
            'name': 'test_dataset_job_3',
            'uuid': 'test-uuid-3',
            'kind': DatasetJobKind.RSA_PSI_DATA_JOIN.name,
            'project_id': 2,
            'result_dataset_id': 5,
            'result_dataset_name': 'output_dataset_2',
            'state': DatasetJobState.PENDING.name,
            'coordinator_id': 0,
            'created_at': ANY,
            'has_stages': False,
            'creator_username': 'test user 3',
        }])

        fake_sorter_param = urllib.parse.quote('fake_time asc')
        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs?order_by={fake_sorter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.BAD_REQUEST)

        sorter_param = urllib.parse.quote('created_at desc')
        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs?order_by={sorter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset_jobs = self.get_response_data(get_response)
        self.assertEqual([dataset_job.get('id') for dataset_job in dataset_jobs], [4, 2, 1])

        filter_param = urllib.parse.quote('(and(state:["SUCCEEDED"])(name~="test_dataset"))')
        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset_jobs = self.get_response_data(get_response)
        self.assertEqual([dataset_job.get('id') for dataset_job in dataset_jobs], [2])

        filter_param = urllib.parse.quote('(kind:["DATA_ALIGNMENT", "IMPORT_SOURCE"])')
        sorter_param = urllib.parse.quote('created_at asc')
        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs?filter={filter_param}&order_by={sorter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset_jobs = self.get_response_data(get_response)
        self.assertEqual([dataset_job.get('id') for dataset_job in dataset_jobs], [1, 2])

        filter_param = urllib.parse.quote('(coordinator_id:[0])')
        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset_jobs = self.get_response_data(get_response)
        self.assertEqual([dataset_job.get('id') for dataset_job in dataset_jobs], [4, 2])

        filter_param = urllib.parse.quote('(input_dataset_id=1)')
        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs?filter={filter_param}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset_jobs = self.get_response_data(get_response)
        self.assertEqual([dataset_job.get('id') for dataset_job in dataset_jobs], [1])


class DatasetJobDefinitionApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def test_get_wrong_dataset_job_definitions(self):
        resp = self.get_helper('/api/v2/dataset_job_definitions/test')
        self.assertEqual(resp.status_code, 400)

    @patch('fedlearner_webconsole.dataset.apis.DatasetJobKind', lambda _: 'fake_handler')
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobConfiger.from_kind',
           lambda *args: FakeDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.dataset.services.DatasetJobService.is_local', lambda *args: True)
    def test_get_dataset_job_definitions(self):
        resp = self.get_helper('/api/v2/dataset_job_definitions/fake_handler')
        self.assertEqual(resp.status_code, 200)
        self.assertResponseDataEqual(
            resp, {
                'variables': [{
                    'name': 'hello',
                    'value_type': 'NUMBER',
                    'typed_value': 1.0,
                    'value': '',
                    'tag': '',
                    'access_mode': 'UNSPECIFIED',
                    'widget_schema': ''
                }, {
                    'name': 'hello_from_job',
                    'value_type': 'NUMBER',
                    'typed_value': 3.0,
                    'tag': '',
                    'value': '',
                    'access_mode': 'UNSPECIFIED',
                    'widget_schema': ''
                }],
                'is_federated': False,
            })

    @patch('fedlearner_webconsole.dataset.apis.DatasetJobKind', lambda _: 'fake_federated_handler')
    @patch('fedlearner_webconsole.dataset.apis.DatasetJobConfiger.from_kind',
           lambda *args: FakeFederatedDatasetJobConfiger(None))
    @patch('fedlearner_webconsole.dataset.services.DatasetJobService.is_local', lambda *args: False)
    def test_get_federated_dataset_job_definitions(self):
        resp = self.get_helper('/api/v2/dataset_job_definitions/FAKE_HANDLER')
        self.assertEqual(resp.status_code, 200)
        self.assertResponseDataEqual(
            resp, {
                'variables': [{
                    'name': 'hello',
                    'value_type': 'NUMBER',
                    'tag': '',
                    'typed_value': 1.0,
                    'value': '',
                    'access_mode': 'UNSPECIFIED',
                    'widget_schema': ''
                }, {
                    'name': 'hello_from_job',
                    'value_type': 'NUMBER',
                    'typed_value': 3.0,
                    'tag': '',
                    'value': '',
                    'access_mode': 'UNSPECIFIED',
                    'widget_schema': ''
                }],
                'is_federated': True,
            })


class DatasetJobApiTest(BaseTestCase):

    @patch('fedlearner_webconsole.dataset.apis.RpcClient.get_dataset_job')
    def test_get_datasetjob(self, mock_get_dataset_job: MagicMock):
        get_response = self.get_helper('/api/v2/projects/1/dataset_jobs/123')
        self.assertEqual(get_response.status_code, 404)

        with db.session_scope() as session:
            participant = Participant(name='test', domain_name='test_domain')
            session.add(participant)
            project = Project(name='test-project')
            session.add(project)
            session.flush([project, participant])
            project_participant = ProjectParticipant(project_id=project.id, participant_id=participant.id)
            session.add(project_participant)

            output_dataset = Dataset(uuid='output_uuid', name='output_dataset')
            session.add(output_dataset)
            session.flush([output_dataset])
            coordinator_dataset_job = DatasetJob(uuid='u12345',
                                                 name='coordinator_dataset_job',
                                                 project_id=project.id,
                                                 kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                                 input_dataset_id=123,
                                                 output_dataset_id=output_dataset.id,
                                                 creator_username='test user',
                                                 time_range=timedelta(hours=1))
            coordinator_dataset_job.set_global_configs(global_configs=dataset_pb2.DatasetJobGlobalConfigs(
                global_configs={'our': dataset_pb2.DatasetJobConfig(dataset_uuid='u123')}))
            context = dataset_pb2.DatasetJobContext(input_data_batch_num_example=1000,
                                                    output_data_batch_num_example=500)
            coordinator_dataset_job.set_context(context)
            session.add(coordinator_dataset_job)
            mock_get_dataset_job.return_value = service_pb2.GetDatasetJobResponse(dataset_job=dataset_pb2.DatasetJob(
                global_configs=coordinator_dataset_job.get_global_configs(),
                scheduler_state=DatasetJobSchedulerState.STOPPED.name,
            ))

            participant_dataset_job = DatasetJob(
                uuid='u54321',
                name='participant_dataset_job',
                project_id=project.id,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=output_dataset.id,
                coordinator_id=participant.id,
                creator_username='test user',
                time_range=timedelta(days=1),
            )
            session.add(participant_dataset_job)
            session.commit()
            coordinator_dataset_job_id = coordinator_dataset_job.id
            participant_dataset_job_id = participant_dataset_job.id

        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs/{coordinator_dataset_job_id}')
        self.assertEqual(get_response.status_code, 200)
        self.assertResponseDataEqual(
            get_response,
            {
                'id': 1,
                'uuid': 'u12345',
                'name': 'coordinator_dataset_job',
                'project_id': 1,
                'kind': 'RSA_PSI_DATA_JOIN',
                'state': 'PENDING',
                'result_dataset_uuid': 'output_uuid',
                'result_dataset_name': 'output_dataset',
                'global_configs': {
                    'global_configs': {
                        'our': {
                            'dataset_uuid': 'u123',
                            'variables': []
                        }
                    }
                },
                'input_data_batch_num_example': 1000,
                'output_data_batch_num_example': 500,
                'coordinator_id': 0,
                'workflow_id': 0,
                'is_ready': False,
                'started_at': 0,
                'finished_at': 0,
                'has_stages': False,
                'creator_username': 'test user',
                'scheduler_state': 'PENDING',
                'time_range': {
                    'days': 0,
                    'hours': 1,
                },
                'scheduler_message': '',
            },
            ignore_fields=['created_at', 'updated_at'],
        )

        get_response = self.get_helper(f'/api/v2/projects/1/dataset_jobs/{participant_dataset_job_id}')
        self.assertEqual(get_response.status_code, 200)
        self.assertResponseDataEqual(
            get_response,
            {
                'id': 2,
                'uuid': 'u54321',
                'name': 'participant_dataset_job',
                'project_id': 1,
                'kind': 'RSA_PSI_DATA_JOIN',
                'state': 'PENDING',
                'result_dataset_uuid': 'output_uuid',
                'result_dataset_name': 'output_dataset',
                'global_configs': {
                    'global_configs': {
                        'our': {
                            'dataset_uuid': 'u123',
                            'variables': []
                        }
                    }
                },
                'input_data_batch_num_example': 0,
                'output_data_batch_num_example': 0,
                'coordinator_id': 1,
                'workflow_id': 0,
                'is_ready': False,
                'started_at': 0,
                'finished_at': 0,
                'has_stages': False,
                'creator_username': 'test user',
                'scheduler_state': 'STOPPED',
                'time_range': {
                    'days': 1,
                    'hours': 0,
                },
                'scheduler_message': '',
            },
            ignore_fields=['created_at', 'updated_at'],
        )
        mock_get_dataset_job.assert_called_once_with(uuid='u54321')

    def test_delete_dataset_job(self):
        # no dataset
        response = self.delete_helper('/api/v2/projects/1/dataset_jobs/1')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # delete successfully
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='test-uuid',
                                     kind=DatasetJobKind.DATA_ALIGNMENT,
                                     state=DatasetJobState.FAILED,
                                     project_id=1,
                                     workflow_id=1,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     coordinator_id=0)
            session.add(dataset_job)
            session.commit()
        response = self.delete_helper('/api/v2/projects/1/dataset_jobs/1')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        with db.session_scope() as session:
            dataset = session.query(DatasetJob).execution_options(include_deleted=True).get(1)
            self.assertIsNotNone(dataset.deleted_at)


class DatasetJobStopApiTest(BaseTestCase):

    def test_no_dataset_job(self):
        response = self.post_helper('/api/v2/projects/1/dataset_jobs/1:stop')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch('fedlearner_webconsole.dataset.apis.DatasetJobController.stop')
    def test_stop_dataset_job(self, mock_stop: MagicMock):
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='u54321',
                project_id=1,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=0,
                coordinator_id=0,
            )
            session.add(dataset_job)
            session.commit()
        response = self.post_helper('/api/v2/projects/1/dataset_jobs/1:stop')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_stop.assert_called_once_with(uuid='u54321')


class DatasetJobStopSchedulerApiTest(BaseTestCase):

    def test_stop_scheduler_dataset_job(self):
        with db.session_scope() as session:
            dataset_job = DatasetJob(id=1,
                                     uuid='u54321',
                                     project_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     input_dataset_id=123,
                                     output_dataset_id=0,
                                     coordinator_id=0,
                                     scheduler_state=DatasetJobSchedulerState.RUNNABLE,
                                     time_range=timedelta(days=1))
            session.add(dataset_job)
            session.commit()
        response = self.post_helper('/api/v2/projects/1/dataset_jobs/1:stop_scheduler')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).get(1)
            self.assertEqual(dataset_job.scheduler_state, DatasetJobSchedulerState.STOPPED)


class DatasetJobStagesApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='dataset_job uuid',
                project_id=1,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=0,
                coordinator_id=0,
            )
            session.add(dataset_job)
            dataset_job_stage_1 = DatasetJobStage(id=1,
                                                  uuid='uuid_1',
                                                  name='default dataset job stage 1',
                                                  project_id=1,
                                                  workflow_id=1,
                                                  created_at=datetime(2022, 1, 1, 0, 0, 0),
                                                  dataset_job_id=1,
                                                  data_batch_id=1,
                                                  event_time=datetime(2022, 1, 15),
                                                  state=DatasetJobState.PENDING)
            session.add(dataset_job_stage_1)
            dataset_job_stage_2 = DatasetJobStage(id=2,
                                                  uuid='uuid_2',
                                                  name='default dataset job stage 2',
                                                  project_id=1,
                                                  workflow_id=2,
                                                  created_at=datetime(2022, 1, 2, 0, 0, 0),
                                                  dataset_job_id=1,
                                                  data_batch_id=1,
                                                  event_time=datetime(2022, 1, 15),
                                                  state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job_stage_2)
            dataset_job_stage_3 = DatasetJobStage(id=3,
                                                  uuid='uuid_3',
                                                  name='default dataset job stage 3',
                                                  project_id=1,
                                                  workflow_id=1,
                                                  created_at=datetime(2022, 1, 3, 0, 0, 0),
                                                  dataset_job_id=1,
                                                  data_batch_id=1,
                                                  event_time=datetime(2022, 1, 15),
                                                  state=DatasetJobState.STOPPED)
            session.add(dataset_job_stage_3)
            session.commit()

    def test_get_dataset_job_stages(self):
        response = self.get_helper('/api/v2/projects/1/dataset_jobs/1/dataset_job_stages')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(response, [{
            'created_at': ANY,
            'dataset_job_id': 1,
            'id': 3,
            'kind': DatasetJobKind.RSA_PSI_DATA_JOIN.name,
            'name': 'default dataset job stage 3',
            'output_data_batch_id': 1,
            'project_id': 1,
            'state': DatasetJobState.STOPPED.name
        }, {
            'created_at': ANY,
            'dataset_job_id': 1,
            'id': 2,
            'kind': DatasetJobKind.RSA_PSI_DATA_JOIN.name,
            'name': 'default dataset job stage 2',
            'output_data_batch_id': 1,
            'project_id': 1,
            'state': DatasetJobState.SUCCEEDED.name
        }, {
            'created_at': ANY,
            'dataset_job_id': 1,
            'id': 1,
            'kind': DatasetJobKind.RSA_PSI_DATA_JOIN.name,
            'name': 'default dataset job stage 1',
            'output_data_batch_id': 1,
            'project_id': 1,
            'state': DatasetJobState.PENDING.name
        }])
        filter_param = urllib.parse.quote('(state:["STOPPED", "SUCCEEDED"])')
        sorter_param = urllib.parse.quote('created_at asc')
        response = self.get_helper(f'/api/v2/projects/1/dataset_jobs/1/dataset_job_stages?\
                page=1&page_size=5&filter={filter_param}&order_by={sorter_param}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual([job_stage.get('id') for job_stage in data], [2, 3])
        self.assertEqual(
            json.loads(response.data).get('page_meta'), {
                'current_page': 1,
                'page_size': 5,
                'total_pages': 1,
                'total_items': 2
            })


class DatasetJobStageApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            dataset_job = DatasetJob(
                id=1,
                uuid='dataset_job uuid',
                project_id=1,
                kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                input_dataset_id=123,
                output_dataset_id=0,
                coordinator_id=0,
            )
            session.add(dataset_job)
            dataset_job_stage_1 = DatasetJobStage(id=1,
                                                  uuid='uuid_1',
                                                  name='default dataset job stage 1',
                                                  project_id=1,
                                                  workflow_id=1,
                                                  created_at=datetime(2022, 1, 1, 0, 0, 0),
                                                  dataset_job_id=1,
                                                  data_batch_id=1,
                                                  event_time=datetime(2022, 1, 15),
                                                  state=DatasetJobState.PENDING,
                                                  coordinator_id=0)
            session.add(dataset_job_stage_1)
            session.commit()

    def test_get_dataset_job_stage(self):
        response = self.get_helper('/api/v2/projects/1/dataset_jobs/1/dataset_job_stages/1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(
            response, {
                'id': 1,
                'uuid': 'uuid_1',
                'workflow_id': 1,
                'dataset_job_id': 1,
                'dataset_job_uuid': 'dataset_job uuid',
                'event_time': to_timestamp(datetime(2022, 1, 15)),
                'is_ready': False,
                'kind': 'RSA_PSI_DATA_JOIN',
                'name': 'default dataset job stage 1',
                'output_data_batch_id': 1,
                'project_id': 1,
                'state': 'PENDING',
                'created_at': ANY,
                'updated_at': ANY,
                'started_at': 0,
                'finished_at': 0,
                'input_data_batch_num_example': 0,
                'output_data_batch_num_example': 0,
                'scheduler_message': '',
            })
        response = self.get_helper('/api/v2/projects/2/dataset_jobs/2/dataset_job_stages/2')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class ChildrenbDatasetsApiTest(BaseTestCase):

    def test_get_sub_dataset_api(self):
        with db.session_scope() as session:
            parent_dataset = Dataset(id=1,
                                     uuid='parent_dataset uuid',
                                     name='parent_dataset',
                                     creator_username='test',
                                     dataset_type=DatasetType.STREAMING,
                                     comment='test comment',
                                     path='/data/dataset/123',
                                     is_published=True,
                                     project_id=1,
                                     dataset_format=DatasetFormat.TABULAR.value)
            session.add(parent_dataset)
            dataset_job = DatasetJob(workflow_id=0,
                                     uuid=resource_uuid(),
                                     project_id=1,
                                     kind=DatasetJobKind.RSA_PSI_DATA_JOIN,
                                     input_dataset_id=1,
                                     output_dataset_id=2,
                                     state=DatasetJobState.SUCCEEDED)
            session.add(dataset_job)
            analyzer_dataset_job = DatasetJob(workflow_id=0,
                                              uuid=resource_uuid(),
                                              project_id=1,
                                              kind=DatasetJobKind.ANALYZER,
                                              input_dataset_id=1,
                                              output_dataset_id=1,
                                              state=DatasetJobState.SUCCEEDED)
            session.add(analyzer_dataset_job)
            child_dataset = Dataset(id=2,
                                    uuid='child_dataset uuid',
                                    name='child_dataset',
                                    creator_username='test',
                                    dataset_type=DatasetType.STREAMING,
                                    comment='test comment',
                                    path='/data/dataset/123',
                                    is_published=True,
                                    project_id=1,
                                    dataset_format=DatasetFormat.TABULAR.value,
                                    dataset_kind=DatasetKindV2.PROCESSED,
                                    store_format=StoreFormat.TFRECORDS)
            session.add(child_dataset)
            export_dataset_job = DatasetJob(workflow_id=0,
                                            uuid=resource_uuid(),
                                            project_id=1,
                                            kind=DatasetJobKind.EXPORT,
                                            input_dataset_id=1,
                                            output_dataset_id=3,
                                            state=DatasetJobState.SUCCEEDED)
            session.add(export_dataset_job)
            export_dataset = Dataset(id=3,
                                     uuid='export_dataset uuid',
                                     name='export_dataset',
                                     creator_username='test',
                                     dataset_type=DatasetType.STREAMING,
                                     comment='test comment',
                                     path='/data/dataset/123',
                                     is_published=False,
                                     project_id=1,
                                     dataset_format=DatasetFormat.TABULAR.value,
                                     dataset_kind=DatasetKindV2.EXPORTED,
                                     store_format=StoreFormat.CSV)
            session.add(export_dataset)
            session.commit()
        response = self.get_helper('/api/v2/datasets/1/children_datasets')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertResponseDataEqual(response, [{
            'id': 2,
            'project_id': 1,
            'name': 'child_dataset',
            'creator_username': 'test',
            'created_at': ANY,
            'path': '/data/dataset/123',
            'dataset_format': 'TABULAR',
            'comment': 'test comment',
            'state_frontend': 'SUCCEEDED',
            'dataset_kind': 'PROCESSED',
            'data_source': ANY,
            'file_size': 0,
            'is_published': True,
            'num_example': 0,
            'uuid': 'child_dataset uuid',
            'total_value': 0,
            'store_format': 'TFRECORDS',
            'dataset_type': 'STREAMING',
            'import_type': 'COPY',
            'publish_frontend_state': 'PUBLISHED',
            'auth_frontend_state': 'AUTH_APPROVED',
            'local_auth_status': 'PENDING',
            'participants_info': {
                'participants_map': {}
            },
        }])


if __name__ == '__main__':
    unittest.main()
