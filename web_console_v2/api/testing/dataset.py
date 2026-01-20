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
from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.dataset.job_configer.base_configer import BaseConfiger
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition, WorkflowDefinition
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.utils.workflow import zip_workflow_variables


class FakeDatasetJobConfiger(BaseConfiger):

    def get_config(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            variables=[Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))],
            job_definitions=[
                JobDefinition(variables=[
                    Variable(
                        name='hello_from_job', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=3))
                ])
            ])

    @property
    def user_variables(self) -> List[common_pb2.Variable]:
        return list(zip_workflow_variables(self.get_config()))

    def auto_config_variables(self, global_configs: DatasetJobGlobalConfigs) -> DatasetJobGlobalConfigs:
        return global_configs

    def config_local_variables(self,
                               global_configs: DatasetJobGlobalConfigs,
                               result_dataset_uuid: str,
                               event_time: Optional[datetime] = None) -> DatasetJobGlobalConfigs:
        del result_dataset_uuid
        return global_configs


class FakeFederatedDatasetJobConfiger(BaseConfiger):

    def get_config(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            variables=[Variable(name='hello', value_type=Variable.ValueType.NUMBER, typed_value=Value(number_value=1))],
            job_definitions=[
                JobDefinition(variables=[
                    Variable(name='hello_from_job',
                             value_type=Variable.ValueType.NUMBER,
                             typed_value=Value(number_value=3))
                ],
                              is_federated=True)
            ])

    @property
    def user_variables(self) -> List[common_pb2.Variable]:
        return list(zip_workflow_variables(self.get_config()))

    def auto_config_variables(self, global_configs: DatasetJobGlobalConfigs) -> DatasetJobGlobalConfigs:
        return global_configs

    def config_local_variables(self,
                               global_configs: DatasetJobGlobalConfigs,
                               result_dataset_uuid: str,
                               event_time: Optional[datetime] = None) -> DatasetJobGlobalConfigs:
        del result_dataset_uuid
        return global_configs


class FakeExecutor(BaseExecutor):

    def get_item_ids(self) -> List[int]:
        return [1, 2, 3, 4]

    def run_item(self, item_id: int) -> ExecutorResult:
        if item_id == 1:
            return ExecutorResult.SUCCEEDED
        if item_id == 2:
            return ExecutorResult.FAILED
        if item_id == 3:
            return ExecutorResult.SKIP
        raise RuntimeError('run fake executor failed')
