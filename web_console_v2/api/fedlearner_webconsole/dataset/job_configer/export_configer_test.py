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

from datetime import datetime
import os
import unittest
from unittest.mock import patch
from google.protobuf.struct_pb2 import Value

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.workflow import zip_workflow_variables
from fedlearner_webconsole.initial_db import _insert_or_update_templates
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, DatasetKindV2, DatasetType
from fedlearner_webconsole.dataset.job_configer.export_configer import ExportConfiger
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobConfig, DatasetJobGlobalConfigs
from fedlearner_webconsole.proto.setting_pb2 import SystemInfo


class ExportConfigersTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            _insert_or_update_templates(session)

            test_project = Project(name='test_project')
            session.add(test_project)
            session.flush([test_project])

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
                                              path=os.path.join(test_input_dataset.path, 'batch/0'))
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
                                               path=os.path.join(test_output_dataset.path, 'batch/0'))
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

            self._input_dataset_uuid = test_input_dataset.uuid
            self._output_dataset_uuid = test_output_dataset.uuid
            self._input_streaming_dataset_uuid = test_input_streaming_dataset.uuid
            self._output_streaming_dataset_uuid = test_output_streaming_dataset.uuid

            session.commit()

    @patch('fedlearner_webconsole.setting.service.SettingService.get_system_info',
           lambda: SystemInfo(domain_name='fl-test_domain.com', pure_domain_name='test_domain'))
    def test_export(self):
        with db.session_scope() as session:
            # This is a test to notify the change of template
            config = ExportConfiger(session).get_config()
            variables = zip_workflow_variables(config)
            self.assertEqual(len(list(variables)), 13)

        with db.session_scope() as session:
            self.assertEqual(len(ExportConfiger(session).user_variables), 8)

        with db.session_scope() as session:
            resp = ExportConfiger(session).auto_config_variables(global_configs=DatasetJobGlobalConfigs(
                global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid)}))
            self.assertEqual(list(resp.global_configs['test_domain'].variables), [])

        # test none_streaming dataset
        with db.session_scope() as session:
            global_configs = ExportConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._input_dataset_uuid)}),
                result_dataset_uuid=self._output_dataset_uuid)
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='dataset_path',
                         value='/data/dataset/test_input_dataset',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='file_format',
                         value='tfrecords',
                         typed_value=Value(string_value='tfrecords'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='batch_name',
                         value='0',
                         typed_value=Value(string_value='0'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='export_path',
                         value='/data/dataset/test_output_dataset/batch/0',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/0'),
                         value_type=Variable.ValueType.STRING),
            ])

        # test streaming dataset
        with db.session_scope() as session:
            global_configs = ExportConfiger(session).config_local_variables(
                global_configs=DatasetJobGlobalConfigs(
                    global_configs={'test_domain': DatasetJobConfig(dataset_uuid=self._input_streaming_dataset_uuid)}),
                result_dataset_uuid=self._output_streaming_dataset_uuid,
                event_time=datetime(2022, 1, 1))
            self.assertEqual(list(global_configs.global_configs['test_domain'].variables), [
                Variable(name='dataset_path',
                         value='/data/dataset/test_input_dataset',
                         typed_value=Value(string_value='/data/dataset/test_input_dataset'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='file_format',
                         value='tfrecords',
                         typed_value=Value(string_value='tfrecords'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='batch_name',
                         value='20220101',
                         typed_value=Value(string_value='20220101'),
                         value_type=Variable.ValueType.STRING),
                Variable(name='export_path',
                         value='/data/dataset/test_output_dataset/batch/20220101',
                         typed_value=Value(string_value='/data/dataset/test_output_dataset/batch/20220101'),
                         value_type=Variable.ValueType.STRING),
            ])


if __name__ == '__main__':
    unittest.main()
