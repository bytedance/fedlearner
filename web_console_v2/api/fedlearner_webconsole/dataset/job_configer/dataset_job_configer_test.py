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

# TODO(liuhehan): split this UT to multi-files
# pylint: disable=protected-access
from datetime import datetime, timedelta
import json
import os
import unittest
from unittest.mock import patch

from google.protobuf.struct_pb2 import Value

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobConfig, DatasetJobGlobalConfigs
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo
from fedlearner_webconsole.utils.workflow import zip_workflow_variables
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.dataset.models import DataBatch, DataSource, Dataset, DatasetJob, DatasetJobKind, \
    DatasetJobState, DatasetKindV2, DatasetMetaInfo, ImportType, DatasetType
from fedlearner_webconsole.dataset.job_configer.import_source_configer import ImportSourceConfiger
from fedlearner_webconsole.dataset.job_configer.data_alignment_configer import DataAlignmentConfiger
from fedlearner_webconsole.dataset.job_configer.rsa_psi_data_join_configer import RsaPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.light_client_rsa_psi_data_join_configer import \
    LightClientRsaPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.ot_psi_data_join_configer import OtPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.hash_data_join_configer import HashDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.analyzer_configer import AnalyzerConfiger


def fake_spark_schema(*args) -> str:
    del args

    return json.dumps({
        'type':
            'struct',
        'fields': [{
            'name': 'raw_id',
            'type': 'integer',
            'nullable': True,
            'metadata': {}
        }, {
            'name': 'f01',
            'type': 'float',
            'nullable': True,
            'metadata': {}
        }, {
            'name': 'image',
            'type': 'binary',
            'nullable': True,
            'metadata': {}
        }]
    })


class DatasetJobConfigersTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.maxDiff = None
        with db.session_scope() as session:
            _insert_or_update_templates(session)

            test_project = Project(name='test_project')
            session.add(test_project)
            session.flush([test_project])

            data_source = DataSource(id=1,
                                     name='test_data_source',
                                     uuid=resource_uuid(),
                                     path='/data/some_data_source/')
            session.add(data_source)

            test_input_dataset = Dataset(id=2,
                                         name='test_input_dataset',
                                         uuid=resource_uuid(),
                                         is_published=False,
                                         project_id=test_project.id,
                                         path='/data/dataset/test_input_dataset',
                                         dataset_kind=DatasetKindV2.RAW)
            session.add(test_input_dataset)
            session.flush([test_input_dataset])

            test_input_data_batch = DataBatch(dataset_id=test_input_dataset.id,
                                              path=os.path.join(test_input_dataset.path, 'batch/test_input_data_batch'))
            session.add(test_input_data_batch)

            test_output_dataset = Dataset(id=3,
                                          name='test_output_dataset',
                                          uuid=resource_uuid(),
                                          is_published=True,
                                          project_id=test_project.id,
                                          path='/data/dataset/test_output_dataset',
                                          dataset_kind=DatasetKindV2.PROCESSED)
            session.add(test_output_dataset)
            session.flush([test_output_dataset])

            test_output_data_batch = DataBatch(dataset_id=test_output_dataset.id,
                                               path=os.path.join(test_output_dataset.path,
                                                                 'batch/test_output_data_batch'))
            session.add(test_output_data_batch)

            test_input_streaming_dataset = Dataset(id=4,
                                                   name='test_input_dataset',
                                                   uuid=resource_uuid(),
                                                   is_published=False,
                                                   project_id=test_project.id,
                                                   path='/data/dataset/test_input_dataset',
                                                   dataset_type=DatasetType.STREAMING,
                                                   dataset_kind=DatasetKindV2.RAW)
            session.add(test_input_streaming_dataset)
            session.flush()

            test_input_streaming_data_batch = DataBatch(dataset_id=test_input_streaming_dataset.id,
                                                        event_time=datetime(2022, 1, 1),
                                                        path=os.path.join(test_input_dataset.path, 'batch/20220101'))
            session.add(test_input_streaming_data_batch)

            test_output_streaming_dataset = Dataset(id=5,
                                                    name='test_output_dataset',
                                                    uuid=resource_uuid(),
                                                    is_published=True,
                                                    project_id=test_project.id,
                                                    path='/data/dataset/test_output_dataset',
                                                    dataset_type=DatasetType.STREAMING,
                                                    dataset_kind=DatasetKindV2.PROCESSED)
            session.add(test_output_streaming_dataset)
            session.flush()

            test_output_streaming_data_batch = DataBatch(dataset_id=test_output_streaming_dataset.id,
                                                         event_time=datetime(2022, 1, 1),
                                                         path=os.path.join(test_output_dataset.path, 'batch/20220101'))
            session.add(test_output_streaming_data_batch)

            self._data_source_uuid = data_source.uuid
            self._input_dataset_uuid = test_input_dataset.uuid
            self._output_dataset_uuid = test_output_dataset.uuid
            self._input_streaming_dataset_uuid = test_input_streaming_dataset.uuid
            self._output_streaming_dataset_uuid = test_output_streaming_dataset.uuid

            session.commit()

    def test_get_data_batch(self):
        # test PSI dataset
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter(Dataset.uuid == self._output_dataset_uuid).first()
            data_batch = ImportSourceConfiger(session)._get_data_batch(dataset=dataset)
            self.assertEqual(data_batch.path, '/data/dataset/test_output_dataset/batch/test_output_data_batch')

        # test STREAMING dataset
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter(Dataset.uuid == self._output_streaming_dataset_uuid).first()
            data_batch = ImportSourceConfiger(session)._get_data_batch(dataset=dataset, event_time=datetime(2022, 1, 1))
            self.assertEqual(data_batch.path, '/data/dataset/test_output_dataset/batch/20220101')

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_import_source(self):
        with db.session_scope() as session:
            # This is a test to notify the change of template
            config = ImportSourceConfiger(session).get_config()
            self.assertEqual(len(config.variables), 22)

        with db.session_scope() as session:
            global_configs = ImportSourceConfiger(session).auto_config_variables(global_configs=DatasetJobGlobalConfigs(
                global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._data_source_uuid)}))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='file_format',
                         value='tfrecords',
                         typed_value=Value(string_value='tfrecords'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='data_type',
                         value='tabular',
                         typed_value=Value(string_value='tabular'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

        with db.session_scope() as session:
            global_configs = ImportSourceConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._data_source_uuid)}),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_batch_path',
                         value='/data/some_data_source/',
                         typed_value=Value(string_value='/data/some_data_source/'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(
                    name='batch_path',
                    value='/data/dataset/test_output_dataset/batch/test_output_data_batch',
                    typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/test_output_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='thumbnail_path',
                         value='/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails',
                         typed_value=Value(
                             string_value='/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='checkers',
                         typed_value=Value(string_value=''),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='import_type',
                         value='COPY',
                         typed_value=Value(string_value='COPY'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='test_output_data_batch',
                         typed_value=Value(string_value='test_output_data_batch'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

        with db.session_scope() as session:
            output_dataset: Dataset = session.query(Dataset).filter(Dataset.uuid == self._output_dataset_uuid).first()
            output_dataset.set_meta_info(DatasetMetaInfo(schema_checkers=['RAW_ID_CHECKER', 'NUMERIC_COLUMNS_CHECKER']))
            output_dataset.import_type = ImportType.NO_COPY
            session.commit()

        with db.session_scope() as session:
            global_configs = ImportSourceConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._data_source_uuid)}),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_batch_path',
                         value='/data/some_data_source/',
                         typed_value=Value(string_value='/data/some_data_source/'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(
                    name='batch_path',
                    value='/data/dataset/test_output_dataset/batch/test_output_data_batch',
                    typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/test_output_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='thumbnail_path',
                         value='/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails',
                         typed_value=Value(
                             string_value='/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='checkers',
                         value='RAW_ID_CHECKER,NUMERIC_COLUMNS_CHECKER',
                         typed_value=Value(string_value='RAW_ID_CHECKER,NUMERIC_COLUMNS_CHECKER'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='import_type',
                         value='NO_COPY',
                         typed_value=Value(string_value='NO_COPY'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='test_output_data_batch',
                         typed_value=Value(string_value='test_output_data_batch'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='skip_analyzer',
                         value='true',
                         typed_value=Value(string_value='true'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

        with db.session_scope() as session:
            dataset_job_streaming = DatasetJob(id=1,
                                               uuid='dataset_job streaming',
                                               project_id=1,
                                               input_dataset_id=1,
                                               output_dataset_id=5,
                                               kind=DatasetJobKind.IMPORT_SOURCE,
                                               state=DatasetJobState.PENDING,
                                               time_range=timedelta(days=1))
            session.add(dataset_job_streaming)
            session.commit()

        # test with event_time
        with db.session_scope() as session:
            global_configs = ImportSourceConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._data_source_uuid)}),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_batch_path',
                         value='/data/some_data_source/20220101',
                         typed_value=Value(string_value='/data/some_data_source/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='batch_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='thumbnail_path',
                         value='/data/dataset/test_output_dataset/meta/20220101/thumbnails',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/meta/20220101/thumbnails'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='checkers',
                         value='',
                         typed_value=Value(string_value=''),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='import_type',
                         value='COPY',
                         typed_value=Value(string_value='COPY'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    @patch('fedlearner_webconsole.dataset.job_configer.data_alignment_configer.FileManager.read', fake_spark_schema)
    def test_data_alignment(self):
        with db.session_scope() as session:
            # This is a test to notify the change of template
            config = DataAlignmentConfiger(session).get_config()
            variables = zip_workflow_variables(config)
            self.assertEqual(len(list(variables)), 18)

        with db.session_scope() as session:
            self.assertEqual(len(DataAlignmentConfiger(session).user_variables), 4)

        with db.session_scope() as session:
            global_configs = DataAlignmentConfiger(session).auto_config_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }))
            for job_config in global_configs.global_configs.values():
                variables = job_config.variables
                input_batch_path_variable = [v for v in variables if v.name == 'json_schema'][0]
                self.assertEqual(input_batch_path_variable.value_type, common_pb2.Variable.ValueType.STRING)
                data_type_variable = [v for v in variables if v.name == 'data_type'][0]
                self.assertEqual(data_type_variable.typed_value.string_value, 'tabular')

        with db.session_scope() as session:
            global_configs = DataAlignmentConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_dataset_uuid)
            variables = global_configs.global_configs['test_domain'].variables
            input_batch_path_variable = [v for v in variables if v.name == 'input_batch_path'][0]
            self.assertEqual(input_batch_path_variable.typed_value.string_value,
                             '/data/dataset/test_input_dataset/batch/test_input_data_batch')
            thumbnail_path_variable = [v for v in variables if v.name == 'thumbnail_path'][0]
            self.assertEqual(thumbnail_path_variable.typed_value.string_value,
                             '/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails')

            variables = global_configs.global_configs['test_domain_2'].variables
            self.assertListEqual([v for v in variables if v.name == 'input_batch_path'], [])
            self.assertListEqual([v for v in variables if v.name == 'thumbnail_path'], [])

        # test with event_time
        with db.session_scope() as session:
            global_configs = DataAlignmentConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_dataset_path',
                         value='/data/dataset/test_input_dataset',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='input_batch_path',
                         value='/data/dataset/test_input_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='thumbnail_path',
                         value='/data/dataset/test_output_dataset/meta/20220101/thumbnails',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/meta/20220101/thumbnails'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_rsa_psi_data_join(self):
        with db.session_scope() as session:
            # This is a test to notify the change of template
            config = RsaPsiDataJoinConfiger(session).get_config()
            variables = zip_workflow_variables(config)
            self.assertEqual(len(list(variables)), 20)

        with db.session_scope() as session:
            self.assertEqual(len(RsaPsiDataJoinConfiger(session).user_variables), 9)

        with db.session_scope() as session:
            global_configs = RsaPsiDataJoinConfiger(session).auto_config_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }))

            for pure_domain_name, job_config in global_configs.global_configs.items():
                if pure_domain_name == 'test_domain':
                    for var in job_config.variables:
                        if var.name == 'role':
                            self.assertEqual(var.typed_value.string_value, 'Leader')
                        elif var.name == 'rsa_key_pem':
                            self.assertIn('-----BEGIN RSA PRIVATE KEY-----', var.typed_value.string_value)
                else:
                    for var in job_config.variables:
                        if var.name == 'role':
                            self.assertEqual(var.typed_value.string_value, 'Follower')
                        elif var.name == 'rsa_key_pem':
                            self.assertIn('-----BEGIN RSA PUBLIC KEY-----', var.typed_value.string_value)

                for var in job_config.variables:
                    if var.name == 'rsa_key_path':
                        self.assertEqual(var.typed_value.string_value, '')

        with db.session_scope() as session:
            global_configs = RsaPsiDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_dataset_uuid)

            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='dataset',
                         value='/data/dataset/test_input_dataset/batch/test_input_data_batch',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/test_input_data_batch'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='output_dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=Variable.ValueType.STRING),
                Variable(
                    name='output_batch_path',
                    value='/data/dataset/test_output_dataset/batch/test_output_data_batch',
                    typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/test_output_data_batch'),
                    value_type=Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='test_output_data_batch',
                         typed_value=Value(string_value='test_output_data_batch'),
                         value_type=Variable.ValueType.STRING),
            ])

        # test with event_time
        with db.session_scope() as session:
            global_configs = RsaPsiDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='dataset',
                         value='/data/dataset/test_input_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_light_client_rsa_psi_data_join(self):
        with db.session_scope() as session:
            global_configs = LightClientRsaPsiDataJoinConfiger(session).auto_config_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid)}))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [])

        with db.session_scope() as session:
            global_configs = LightClientRsaPsiDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain':
                            DatasetJobConfig(dataset_uuid=self._input_dataset_uuid,
                                             variables=[
                                                 common_pb2.Variable(name='input_dataset_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='input_batch_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='output_dataset_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='output_batch_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                             ])
                    }),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                common_pb2.Variable(name='input_dataset_path',
                                    typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(
                    name='input_batch_path',
                    typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/test_input_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='output_dataset_path',
                                    typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(
                    name='output_batch_path',
                    typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/test_output_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='output_batch_name',
                                    value='test_output_data_batch',
                                    typed_value=Value(string_value='test_output_data_batch'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])
        # test with event_time
        with db.session_scope() as session:
            global_configs = LightClientRsaPsiDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_dataset_path',
                         value='/data/dataset/test_input_dataset',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='input_batch_path',
                         value='/data/dataset/test_input_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_ot_psi_data_join_configer(self):
        with db.session_scope() as session:
            global_configs = OtPsiDataJoinConfiger(session).auto_config_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain':
                            DatasetJobConfig(dataset_uuid=self._input_dataset_uuid,
                                             variables=[
                                                 common_pb2.Variable(name='role',
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                             ]),
                        'test_domain_2':
                            DatasetJobConfig(dataset_uuid='u12345',
                                             variables=[
                                                 common_pb2.Variable(name='role',
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                             ])
                    }))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                common_pb2.Variable(name='role',
                                    typed_value=Value(string_value='server'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])
            self.assertEqual(list(global_configs.global_configs['test_domain_2'].variables), [
                common_pb2.Variable(name='role',
                                    typed_value=Value(string_value='client'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])

        with db.session_scope() as session:
            global_configs = OtPsiDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain':
                            DatasetJobConfig(dataset_uuid=self._input_dataset_uuid,
                                             variables=[
                                                 common_pb2.Variable(name='input_dataset_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='input_batch_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='output_dataset_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='output_batch_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                             ])
                    }),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                common_pb2.Variable(name='input_dataset_path',
                                    typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(
                    name='input_batch_path',
                    typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/test_input_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='output_dataset_path',
                                    typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(
                    name='output_batch_path',
                    typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/test_output_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='output_batch_name',
                                    value='test_output_data_batch',
                                    typed_value=Value(string_value='test_output_data_batch'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])
        # test with event_time
        with db.session_scope() as session:
            global_configs = OtPsiDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_dataset_path',
                         value='/data/dataset/test_input_dataset',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='input_batch_path',
                         value='/data/dataset/test_input_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_hash_data_join_configer(self):
        with db.session_scope() as session:
            global_configs = HashDataJoinConfiger(session).auto_config_variables(global_configs=DatasetJobGlobalConfigs(
                global_configs={
                    'test_domain':
                        DatasetJobConfig(dataset_uuid=self._input_dataset_uuid,
                                         variables=[
                                             common_pb2.Variable(name='role',
                                                                 value_type=common_pb2.Variable.ValueType.STRING),
                                         ]),
                    'test_domain_2':
                        DatasetJobConfig(dataset_uuid='u12345',
                                         variables=[
                                             common_pb2.Variable(name='role',
                                                                 value_type=common_pb2.Variable.ValueType.STRING),
                                         ])
                }))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                common_pb2.Variable(name='role',
                                    typed_value=Value(string_value='server'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])
            self.assertEqual(list(global_configs.global_configs['test_domain_2'].variables), [
                common_pb2.Variable(name='role',
                                    typed_value=Value(string_value='client'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])

        with db.session_scope() as session:
            global_configs = HashDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain':
                            DatasetJobConfig(dataset_uuid=self._input_dataset_uuid,
                                             variables=[
                                                 common_pb2.Variable(name='input_dataset_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='input_batch_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='output_dataset_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                                 common_pb2.Variable(name='output_batch_path',
                                                                     typed_value=Value(string_value=''),
                                                                     value_type=common_pb2.Variable.ValueType.STRING),
                                             ])
                    }),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                common_pb2.Variable(name='input_dataset_path',
                                    typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(
                    name='input_batch_path',
                    typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/test_input_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='output_dataset_path',
                                    typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(
                    name='output_batch_path',
                    typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/test_output_data_batch'),
                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='output_batch_name',
                                    value='test_output_data_batch',
                                    typed_value=Value(string_value='test_output_data_batch'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])
        # test with event_time
        with db.session_scope() as session:
            global_configs = HashDataJoinConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={
                        'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid),
                        'test_domain_2': DatasetJobConfig(dataset_uuid='u12345')
                    }),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='input_dataset_path',
                         value='/data/dataset/test_input_dataset',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='input_batch_path',
                         value='/data/dataset/test_input_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_dataset_path',
                         value='/data/dataset/test_output_dataset',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_analyzer_configer(self):
        with db.session_scope() as session:
            # This is a test to notify the change of template
            config = AnalyzerConfiger(session).get_config()
            self.assertEqual(len(config.variables), 14)

        with db.session_scope() as session:
            global_configs = AnalyzerConfiger(session).auto_config_variables(global_configs=DatasetJobGlobalConfigs(
                global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._data_source_uuid)}))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                common_pb2.Variable(name='input_batch_path',
                                    value='/data/some_data_source/',
                                    typed_value=Value(string_value='/data/some_data_source/'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
                common_pb2.Variable(name='data_type',
                                    value='tabular',
                                    typed_value=Value(string_value='tabular'),
                                    value_type=common_pb2.Variable.ValueType.STRING),
            ])

        with db.session_scope() as session:
            global_configs = AnalyzerConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._data_source_uuid)}),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='thumbnail_path',
                         value='/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails',
                         typed_value=Value(
                             string_value='/data/dataset/test_output_dataset/meta/test_output_data_batch/thumbnails'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='test_output_data_batch',
                         typed_value=Value(string_value='test_output_data_batch'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])

        # test with event_time
        with db.session_scope() as session:
            global_configs = AnalyzerConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid)}),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='thumbnail_path',
                         value='/data/dataset/test_output_dataset/meta/20220101/thumbnails',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/meta/20220101/thumbnails'),
                         value_type=common_pb2.Variable.ValueType.STRING),
                Variable(name='output_batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=common_pb2.Variable.ValueType.STRING),
            ])


if __name__ == '__main__':
    unittest.main()
