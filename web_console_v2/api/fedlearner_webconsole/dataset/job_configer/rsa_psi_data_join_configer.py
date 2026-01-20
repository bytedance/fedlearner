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

from typing import Tuple, List, Optional
import rsa

from fedlearner_webconsole.dataset.models import Dataset, ProcessedDataset
from fedlearner_webconsole.dataset.job_configer.base_configer import BaseConfiger, get_my_pure_domain_name, \
    set_variable_value_to_job_config
from fedlearner_webconsole.dataset.data_path import get_batch_data_path
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs
from fedlearner_webconsole.utils.workflow import zip_workflow_variables
from fedlearner_webconsole.workflow_template.service import WorkflowTemplateService
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.proto import common_pb2, workflow_definition_pb2


class RsaPsiDataJoinConfiger(BaseConfiger):
    USER_VARIABLES_NAME_SET = {
        'fedlearner_image_version',
        'num_partitions',
        'raw_worker_cpu',
        'raw_worker_mem',
        'batch_size',
        'psi_worker_cpu',
        'psi_worker_mem',
        'master_cpu',
        'master_mem',
    }

    @staticmethod
    def _generate_rsa_key_pair(length: int = 1024) -> Tuple[str, str]:
        """generate rsa key pair in pem format

        Args:
            length (int, optional): bits for generate private key. Defaults to 1024.

        Returns:
            Tuple[str, str]: PublicKey PEM, PrivateKey PEM
        """
        # Note that we generate rsa keys in current thread, which will slow down api response.
        # DONT USE POOLSIZE ARGUMENT!!!!
        # TODO(wangsen.0914): optimize this using async job_scheduler to call this func.
        public_key, private_key = rsa.newkeys(length)
        return public_key.save_pkcs1(format='PEM').decode(), private_key.save_pkcs1(format='PEM').decode()

    def get_config(self) -> workflow_definition_pb2.WorkflowDefinition:
        template = WorkflowTemplateService(
            self._session).get_workflow_template(name='sys-preset-psi-data-join-analyzer')
        return template.get_config()

    @property
    def user_variables(self) -> List[common_pb2.Variable]:
        real_user_variables = []
        for variable in zip_workflow_variables(self.get_config()):
            if variable.name in self.USER_VARIABLES_NAME_SET:
                real_user_variables.append(variable)

        return real_user_variables

    def auto_config_variables(self, global_configs: DatasetJobGlobalConfigs) -> DatasetJobGlobalConfigs:
        my_domain_name = get_my_pure_domain_name()
        job_config = global_configs.global_configs[my_domain_name]
        dataset = self._session.query(Dataset).filter(Dataset.uuid == job_config.dataset_uuid).first()
        if dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {job_config.dataset_uuid}')

        public_key_pem, private_key_pem = self._generate_rsa_key_pair()
        for pure_domain_name, job_config in global_configs.global_configs.items():
            if pure_domain_name == my_domain_name:
                role_variable = make_variable(name='role', typed_value='Leader')
                set_variable_value_to_job_config(job_config, role_variable)
                rsa_key_pem_variable = make_variable(name='rsa_key_pem', typed_value=private_key_pem)
                set_variable_value_to_job_config(job_config, rsa_key_pem_variable)

            else:
                role_variable = make_variable(name='role', typed_value='Follower')
                set_variable_value_to_job_config(job_config, role_variable)
                rsa_key_pem_variable = make_variable(name='rsa_key_pem', typed_value=public_key_pem)
                set_variable_value_to_job_config(job_config, rsa_key_pem_variable)

            rsa_key_path_variable = make_variable(name='rsa_key_path', typed_value='')
            set_variable_value_to_job_config(job_config, rsa_key_path_variable)
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
        output_dataset = self._session.query(ProcessedDataset).filter(
            ProcessedDataset.uuid == result_dataset_uuid).first()
        if output_dataset is None:
            raise InvalidArgumentException(details=f'failed to find dataset {result_dataset_uuid}')

        input_batch = self._get_data_batch(input_dataset, event_time)
        output_batch = self._get_data_batch(output_dataset, event_time)

        input_batch_path = get_batch_data_path(input_batch)

        dataset_variable = make_variable(name='dataset', typed_value=input_batch_path)
        set_variable_value_to_job_config(job_config, dataset_variable)

        output_dataset_path_variable = make_variable(name='output_dataset_path', typed_value=output_dataset.path)
        set_variable_value_to_job_config(job_config, output_dataset_path_variable)

        output_batch_path_variable = make_variable(name='output_batch_path', typed_value=output_batch.path)
        set_variable_value_to_job_config(job_config, output_batch_path_variable)

        output_batch_name_variable = make_variable(name='output_batch_name', typed_value=output_batch.batch_name)
        set_variable_value_to_job_config(job_config, output_batch_name_variable)

        return global_configs
