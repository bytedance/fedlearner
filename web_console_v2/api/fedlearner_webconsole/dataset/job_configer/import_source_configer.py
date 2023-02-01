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

from typing import List, Optional

from fedlearner_webconsole.dataset.models import (Dataset, DatasetFormat, DatasetKindV2, ImportType, StoreFormat,
                                                  DatasetType)
from fedlearner_webconsole.dataset.job_configer.base_configer import BaseConfiger, get_my_pure_domain_name, \
    set_variable_value_to_job_config, filter_user_variables
from fedlearner_webconsole.dataset.dataset_directory import DatasetDirectory
from fedlearner_webconsole.dataset.util import parse_event_time_to_daily_folder_name, \
    parse_event_time_to_hourly_folder_name
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs
from fedlearner_webconsole.utils.workflow import zip_workflow_variables
from fedlearner_webconsole.workflow_template.service import WorkflowTemplateService
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.proto import common_pb2, workflow_definition_pb2


class ImportSourceConfiger(BaseConfiger):

    def get_config(self) -> workflow_definition_pb2.WorkflowDefinition:
        template = WorkflowTemplateService(self._session).get_workflow_template(name='sys-preset-converter-analyzer')
        return template.get_config()

    @property
    def user_variables(self) -> List[common_pb2.Variable]:
        # return variables which tag is RESOURCE_ALLOCATION or INPUT_PARAM
        return filter_user_variables(list(zip_workflow_variables(self.get_config())))

    def auto_config_variables(self, global_configs: DatasetJobGlobalConfigs) -> DatasetJobGlobalConfigs:
        my_domain_name = get_my_pure_domain_name()
        job_config = global_configs.global_configs[my_domain_name]
        input_dataset: Dataset = self._session.query(Dataset).filter(Dataset.uuid == job_config.dataset_uuid).first()
        if input_dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {job_config.dataset_uuid}')

        if input_dataset.store_format is None:
            if input_dataset.dataset_kind == DatasetKindV2.SOURCE:
                raise InvalidArgumentException(f'data_source {input_dataset.name} is too old and has no store_format, \
                                please create a new data_source')
            input_dataset.store_format = StoreFormat.TFRECORDS
        file_format_variable = make_variable(name='file_format', typed_value=input_dataset.store_format.name.lower())
        set_variable_value_to_job_config(job_config, file_format_variable)
        data_type_variable = make_variable(name='data_type',
                                           typed_value=DatasetFormat(input_dataset.dataset_format).name.lower())
        set_variable_value_to_job_config(job_config, data_type_variable)

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

        if output_dataset.dataset_type == DatasetType.PSI:
            input_batch_path = input_dataset.path
        else:
            if output_dataset.parent_dataset_job.is_hourly_cron():
                folder_name = parse_event_time_to_hourly_folder_name(event_time)
            else:
                folder_name = parse_event_time_to_daily_folder_name(event_time)
            input_batch_path = os.path.join(input_dataset.path, folder_name)
        output_data_batch = self._get_data_batch(output_dataset, event_time)
        output_batch_path = output_data_batch.path
        output_batch_name = output_data_batch.batch_name
        output_dataset_path = output_dataset.path
        thumbnail_path = DatasetDirectory(dataset_path=output_dataset_path).thumbnails_path(
            batch_name=output_batch_name)
        schema_checkers = list(output_dataset.get_meta_info().schema_checkers)

        # Note: Following vairables's name should be equal to template `sys-preset-converter-analyzer`
        input_batch_path_variable = make_variable(name='input_batch_path', typed_value=input_batch_path)
        set_variable_value_to_job_config(job_config, input_batch_path_variable)

        dataset_path_variable = make_variable(name='dataset_path', typed_value=output_dataset_path)
        set_variable_value_to_job_config(job_config, dataset_path_variable)

        batch_path_variable = make_variable(name='batch_path', typed_value=output_batch_path)
        set_variable_value_to_job_config(job_config, batch_path_variable)

        thumbnail_path_variable = make_variable(name='thumbnail_path', typed_value=thumbnail_path)
        set_variable_value_to_job_config(job_config, thumbnail_path_variable)

        schema_checkers_variable = make_variable(name='checkers', typed_value=','.join(schema_checkers))
        set_variable_value_to_job_config(job_config, schema_checkers_variable)

        import_type_variable = make_variable(name='import_type', typed_value=output_dataset.import_type.name)
        set_variable_value_to_job_config(job_config, import_type_variable)

        output_batch_name_variable = make_variable(name='output_batch_name', typed_value=output_batch_name)
        set_variable_value_to_job_config(job_config, output_batch_name_variable)

        if output_dataset.import_type == ImportType.NO_COPY:
            skip_analyzer_variable = make_variable(name='skip_analyzer', typed_value='true')
            set_variable_value_to_job_config(job_config, skip_analyzer_variable)

        return global_configs
