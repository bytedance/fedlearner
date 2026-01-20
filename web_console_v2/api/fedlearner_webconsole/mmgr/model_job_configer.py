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

import os
import logging
from typing import Optional, List
from sqlalchemy.orm.session import Session
from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobKind, DataBatch
from fedlearner_webconsole.mmgr.models import Model, ModelJobType
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.workflow_template.utils import make_variable, set_value
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobConfig
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.const import SYS_PRESET_TREE_TEMPLATE, SYS_PRESET_VERTICAL_NN_TEMPLATE, \
    SYS_PRESET_HORIZONTAL_NN_TEMPLATE, SYS_PRESET_HORIZONTAL_NN_EVAL_TEMPLATE

LOAD_MODEL_NAME = 'load_model_name'


def set_load_model_name(config: ModelJobConfig, model_name: str):
    """Set variable of load_model_name inplace"""
    for variable in config.variables:
        if variable.name == LOAD_MODEL_NAME:
            assert variable.value_type == Variable.ValueType.STRING
            variable.value = model_name
            variable.typed_value.MergeFrom(Value(string_value=model_name))


def get_sys_template_id(session: Session, algorithm_type: AlgorithmType, model_job_type: ModelJobType) -> Optional[int]:
    template_name = None
    if algorithm_type == AlgorithmType.NN_VERTICAL:
        template_name = SYS_PRESET_VERTICAL_NN_TEMPLATE
    if algorithm_type == AlgorithmType.NN_HORIZONTAL:
        if model_job_type == ModelJobType.TRAINING:
            template_name = SYS_PRESET_HORIZONTAL_NN_TEMPLATE
        else:
            template_name = SYS_PRESET_HORIZONTAL_NN_EVAL_TEMPLATE
    if algorithm_type == AlgorithmType.TREE_VERTICAL:
        template_name = SYS_PRESET_TREE_TEMPLATE
    if template_name:
        template_id = session.query(WorkflowTemplate.id).filter_by(name=template_name).first()
        if template_id is not None:
            return template_id[0]
    return None


def _set_variable(variables: List[Variable], new_variable: Variable):
    for variable in variables:
        if variable.name == new_variable.name:
            variable.CopyFrom(new_variable)
            return
    raise Exception(f'variable {new_variable.name} is not found')


class ModelJobConfiger:

    def __init__(self, session: Session, model_job_type: ModelJobType, algorithm_type: AlgorithmType, project_id: int):
        self._session = session
        self.model_job_type = model_job_type
        self.algorithm_type = algorithm_type
        self.project_id = project_id

    @staticmethod
    def _init_config(config: WorkflowDefinition, variables: List[Variable]):
        assert len(config.job_definitions) == 1
        new_dict = {i.name: i for i in variables}
        for var in config.job_definitions[0].variables:
            if var.name in new_dict:
                var.typed_value.CopyFrom(new_dict[var.name].typed_value)
                var.value = new_dict[var.name].value

    def _get_config(self) -> WorkflowDefinition:
        template_id = get_sys_template_id(session=self._session,
                                          algorithm_type=self.algorithm_type,
                                          model_job_type=self.model_job_type)
        if template_id is None:
            raise InternalException('preset template is not found')
        template: WorkflowTemplate = self._session.query(WorkflowTemplate).get(template_id)
        return template.get_config()

    def get_dataset_variables(self, dataset_id: Optional[int], data_batch_id: Optional[int] = None) -> List[Variable]:
        if dataset_id is None:
            return []
        dataset: Dataset = self._session.query(Dataset).get(dataset_id)
        dataset_job: DatasetJob = self._session.query(DatasetJob).filter_by(output_dataset_id=dataset_id).first()
        if dataset_job is None:
            raise InvalidArgumentException(f'dataset job for dataset {dataset_id} is not found')
        data_source = dataset.get_data_source()
        data_path = os.path.join(dataset.path, 'batch')
        if data_batch_id is not None:
            data_batch = self._session.query(DataBatch).get(data_batch_id)
            data_path = data_batch.path
        # TODO(hangweiqiang): use data path for all kind, and set file_wildcard for nn
        variables = []
        if dataset_job.kind == DatasetJobKind.RSA_PSI_DATA_JOIN:
            # there is no data_source in nn horizontal preset template
            if self.algorithm_type != AlgorithmType.NN_HORIZONTAL:
                variables.append(make_variable(name='data_source', typed_value=data_source))
            variables.append(make_variable(name='data_path', typed_value=''))
            if self.algorithm_type == AlgorithmType.TREE_VERTICAL:
                variables.append(make_variable(name='file_wildcard', typed_value='*.data'))
        if dataset_job.kind in [
                DatasetJobKind.OT_PSI_DATA_JOIN, DatasetJobKind.HASH_DATA_JOIN, DatasetJobKind.DATA_ALIGNMENT,
                DatasetJobKind.IMPORT_SOURCE
        ]:
            # there is no data_source in nn horizontal preset template
            if self.algorithm_type != AlgorithmType.NN_HORIZONTAL:
                variables.append(make_variable(name='data_source', typed_value=''))
            variables.append(make_variable(name='data_path', typed_value=data_path))
            if self.algorithm_type == AlgorithmType.TREE_VERTICAL:
                variables.append(make_variable(name='file_wildcard', typed_value='**/part*'))
        return variables

    def get_config(self, dataset_id: int, model_id: Optional[int],
                   model_job_config: ModelJobConfig) -> WorkflowDefinition:
        """get local workflow config from model_job_config"""
        config = self._get_config()
        self._init_config(config=config, variables=model_job_config.variables)
        mode = 'train' if self.model_job_type == ModelJobType.TRAINING else 'eval'
        variables = config.job_definitions[0].variables
        # there is no mode variable in nn horizontal preset template
        if self.algorithm_type != AlgorithmType.NN_HORIZONTAL:
            _set_variable(variables=variables, new_variable=make_variable(name='mode', typed_value=mode))
        dataset_variables = self.get_dataset_variables(dataset_id=dataset_id)
        for var in dataset_variables:
            _set_variable(variables=variables, new_variable=var)
        if model_job_config.algorithm_uuid:
            algorithm = AlgorithmFetcher(self.project_id).get_algorithm(model_job_config.algorithm_uuid)
            parameter = model_job_config.algorithm_parameter
            algo_dict = {
                'algorithmId': algorithm.id,
                'algorithmUuid': algorithm.uuid,
                'algorithmProjectId': algorithm.algorithm_project_id,
                'algorithmProjectUuid': algorithm.algorithm_project_uuid,
                'participantId': algorithm.participant_id,
                'path': algorithm.path,
                'config': to_dict(parameter)['variables']
            }
            variables = config.job_definitions[0].variables
            for variable in variables:
                if variable.name == 'algorithm':
                    set_value(variable=variable, typed_value=algo_dict)
        if model_id is not None:
            model: Model = self._session.query(Model).get(model_id)
            _set_variable(variables=variables,
                          new_variable=make_variable(name='load_model_name', typed_value=model.job_name()))
        return config

    # TODO(hangweiqiang): remove this function after ModelJobConfig is used
    def set_dataset(self, config: WorkflowDefinition, dataset_id: Optional[int], data_batch_id: Optional[int] = None):
        variables = config.job_definitions[0].variables
        dataset_variables = self.get_dataset_variables(dataset_id=dataset_id, data_batch_id=data_batch_id)
        names = {variable.name for variable in variables}
        for variable in dataset_variables:
            # check existence of variable in config for backward compatibility
            if variable.name in names:
                _set_variable(variables=variables, new_variable=variable)
            else:
                logging.info(f'[set_dataset] variable {variable.name} is not found in config')
