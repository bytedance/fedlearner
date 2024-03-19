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

import abc
from datetime import datetime

from typing import List, Optional
from sqlalchemy.orm import Session

from fedlearner_webconsole.dataset.models import Dataset, DataBatch, DatasetType
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.proto import common_pb2, workflow_definition_pb2
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


def get_my_pure_domain_name() -> str:
    """Get pure domain name of our side

    Returns:
        str: pure domain name
    """
    return SettingService.get_system_info().pure_domain_name


def set_variable_value_to_job_config(job_config: dataset_pb2.DatasetJobConfig, target_variable: common_pb2.Variable):
    for variable in job_config.variables:
        if variable.name == target_variable.name and variable.value_type == target_variable.value_type:
            variable.typed_value.CopyFrom(target_variable.typed_value)
            break
    else:
        job_config.variables.append(target_variable)


def filter_user_variables(variables: List[common_pb2.Variable]) -> List[common_pb2.Variable]:
    user_variables = []
    for variable in variables:
        if variable.tag in ['RESOURCE_ALLOCATION', 'INPUT_PARAM']:
            user_variables.append(variable)
    return user_variables


class BaseConfiger(metaclass=abc.ABCMeta):
    """This is base interface aimed to config dataset_job global_configs for different job kind
    Routines:
        user_variables:
            Usage: Get a list of variables that one can configure itself.
            When: [Coordinator] API user gets the dataset_job definitions.
        auto_config_variables:
            Usage: Auto config some variables that are needed real job without letting users know.
            When: [Coordinator] API Layer that creates the dataset_job resource.
        config_local_vairables:
            Usage: Config some local variables that're sensitive to each participants.
            When: [Participant] DatasetJob Scheduler of each participants
    """

    def __init__(self, session: Session):
        self._session = session

    @abc.abstractmethod
    def get_config(self) -> workflow_definition_pb2.WorkflowDefinition:
        """Get workflow_definition of this dataset_job_kind

        Returns:
            workflow_definition_pb2.WorkflowDefinition: workflow definition according to given kind
        """

    @property
    @abc.abstractmethod
    def user_variables(self) -> List[common_pb2.Variable]:
        pass

    @abc.abstractmethod
    def auto_config_variables(self, global_configs: DatasetJobGlobalConfigs) -> DatasetJobGlobalConfigs:
        pass

    @abc.abstractmethod
    def config_local_variables(self,
                               global_configs: DatasetJobGlobalConfigs,
                               result_dataset_uuid: str,
                               event_time: Optional[datetime] = None) -> DatasetJobGlobalConfigs:
        pass

    def _get_data_batch(self, dataset: Dataset, event_time: Optional[datetime] = None) -> DataBatch:
        if dataset.dataset_type == DatasetType.PSI:
            return dataset.get_single_batch()
        data_batch: DataBatch = self._session.query(DataBatch).filter(DataBatch.dataset_id == dataset.id).filter(
            DataBatch.event_time == event_time).first()
        if data_batch is None:
            raise InvalidArgumentException(
                details=f'failed to find data_batch, event_time: {to_timestamp(event_time)}, \
                    dataset id: {dataset.id}')
        return data_batch
