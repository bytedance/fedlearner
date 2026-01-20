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
import json
import os

from typing import List, Optional

from fedlearner_webconsole.dataset.models import Dataset, DatasetFormat
from fedlearner_webconsole.dataset.job_configer.base_configer import BaseConfiger, get_my_pure_domain_name, \
    set_variable_value_to_job_config
from fedlearner_webconsole.dataset.dataset_directory import DatasetDirectory
from fedlearner_webconsole.dataset.data_path import get_batch_data_path
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs
from fedlearner_webconsole.utils.schema import spark_schema_to_json_schema
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.workflow import zip_workflow_variables
from fedlearner_webconsole.workflow_template.service import WorkflowTemplateService
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.proto import common_pb2, workflow_definition_pb2


class DataAlignmentConfiger(BaseConfiger):
    USER_VARIABLES_NAME_SET = {
        'driver_cores',
        'driver_mem',
        'executor_cores',
        'executor_mem',
    }

    def get_config(self) -> workflow_definition_pb2.WorkflowDefinition:
        template = WorkflowTemplateService(self._session).get_workflow_template(name='sys-preset-alignment-task')
        return template.get_config()

    @property
    def user_variables(self) -> List[common_pb2.Variable]:
        real_user_variables = []
        for variable in zip_workflow_variables(self.get_config()):
            if variable.name in self.USER_VARIABLES_NAME_SET:
                real_user_variables.append(variable)

        return real_user_variables

    def auto_config_variables(
            self, global_configs: dataset_pb2.DatasetJobGlobalConfigs) -> dataset_pb2.DatasetJobGlobalConfigs:
        my_domain_name = get_my_pure_domain_name()
        job_config = global_configs.global_configs[my_domain_name]
        dataset = self._session.query(Dataset).filter(Dataset.uuid == job_config.dataset_uuid).first()
        if dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {job_config.dataset_uuid}')

        dataset_path = dataset.path

        spark_schema = FileManager().read(os.path.join(dataset_path, 'schema.json'))
        json_schema_str = json.dumps(spark_schema_to_json_schema(json.loads(spark_schema)))
        for job_config in global_configs.global_configs.values():
            json_schema_variable = make_variable(name='json_schema', typed_value=json_schema_str)
            set_variable_value_to_job_config(job_config, json_schema_variable)
            data_type_variable = make_variable(name='data_type',
                                               typed_value=DatasetFormat(dataset.dataset_format).name.lower())
            set_variable_value_to_job_config(job_config, data_type_variable)
        return global_configs

    def config_local_variables(self,
                               global_configs: DatasetJobGlobalConfigs,
                               result_dataset_uuid: str,
                               event_time: Optional[datetime] = None) -> DatasetJobGlobalConfigs:
        my_domain_name = get_my_pure_domain_name()
        job_config = global_configs.global_configs[my_domain_name]

        input_dataset = self._session.query(Dataset).filter(Dataset.uuid == job_config.dataset_uuid).first()
        if input_dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {job_config.dataset_uuid}')

        output_dataset = self._session.query(Dataset).filter(Dataset.uuid == result_dataset_uuid).first()
        if output_dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {result_dataset_uuid}')

        input_batch = self._get_data_batch(input_dataset, event_time)
        output_batch = self._get_data_batch(output_dataset, event_time)
        input_batch_path = get_batch_data_path(input_batch)
        output_dataset_path = output_dataset.path
        output_batch_path = output_batch.path
        output_batch_name = output_batch.batch_name
        thumbnail_path = DatasetDirectory(dataset_path=output_dataset_path).thumbnails_path(
            batch_name=output_batch_name)

        input_dataset_path_variable = make_variable(name='input_dataset_path', typed_value=input_dataset.path)
        set_variable_value_to_job_config(job_config, input_dataset_path_variable)

        input_batch_path_variable = make_variable(name='input_batch_path', typed_value=input_batch_path)
        set_variable_value_to_job_config(job_config, input_batch_path_variable)

        output_dataset_path_variable = make_variable(name='output_dataset_path', typed_value=output_dataset_path)
        set_variable_value_to_job_config(job_config, output_dataset_path_variable)

        output_batch_path_variable = make_variable(name='output_batch_path', typed_value=output_batch_path)
        set_variable_value_to_job_config(job_config, output_batch_path_variable)

        thumbnail_path_variable = make_variable(name='thumbnail_path', typed_value=thumbnail_path)
        set_variable_value_to_job_config(job_config, thumbnail_path_variable)

        output_batch_name_variable = make_variable(name='output_batch_name', typed_value=output_batch_name)
        set_variable_value_to_job_config(job_config, output_batch_name_variable)

        return global_configs
