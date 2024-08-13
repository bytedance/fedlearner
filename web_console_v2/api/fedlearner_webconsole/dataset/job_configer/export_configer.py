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

from typing import List, Optional

from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.dataset.job_configer.base_configer import BaseConfiger, filter_user_variables, \
    get_my_pure_domain_name, set_variable_value_to_job_config
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs
from fedlearner_webconsole.utils.workflow import zip_workflow_variables
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.workflow_template.service import WorkflowTemplateService
from fedlearner_webconsole.proto import common_pb2, workflow_definition_pb2


class ExportConfiger(BaseConfiger):

    def get_config(self) -> workflow_definition_pb2.WorkflowDefinition:
        template = WorkflowTemplateService(self._session).get_workflow_template(name='sys-preset-export-dataset')
        return template.get_config()

    @property
    def user_variables(self) -> List[common_pb2.Variable]:
        # return variables which tag is RESOURCE_ALLOCATION or INPUT_PARAM
        return filter_user_variables(list(zip_workflow_variables(self.get_config())))

    def auto_config_variables(self, global_configs: DatasetJobGlobalConfigs) -> DatasetJobGlobalConfigs:
        return global_configs

    def config_local_variables(self,
                               global_configs: DatasetJobGlobalConfigs,
                               result_dataset_uuid: str,
                               event_time: Optional[datetime] = None) -> DatasetJobGlobalConfigs:
        my_domain_name = get_my_pure_domain_name()
        job_config = global_configs.global_configs[my_domain_name]

        input_dataset: Dataset = self._session.query(Dataset).filter(Dataset.uuid == job_config.dataset_uuid).first()
        if input_dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {job_config.dataset_uuid}')

        output_dataset: Dataset = self._session.query(Dataset).filter(Dataset.uuid == result_dataset_uuid).first()
        if output_dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {result_dataset_uuid}')

        input_batch = self._get_data_batch(input_dataset, event_time)
        output_batch = self._get_data_batch(output_dataset, event_time)

        dataset_path_variable = make_variable(name='dataset_path', typed_value=input_dataset.path)
        set_variable_value_to_job_config(job_config, dataset_path_variable)

        file_format_variable = make_variable(name='file_format', typed_value=input_dataset.store_format.name.lower())
        set_variable_value_to_job_config(job_config, file_format_variable)

        batch_name_variable = make_variable(name='batch_name', typed_value=input_batch.batch_name)
        set_variable_value_to_job_config(job_config, batch_name_variable)

        export_path_variable = make_variable(name='export_path', typed_value=output_batch.path)
        set_variable_value_to_job_config(job_config, export_path_variable)

        return global_configs
