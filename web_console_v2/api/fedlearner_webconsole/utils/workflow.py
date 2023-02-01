# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from typing import Generator, List

from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition


def build_job_name(workflow_uuid: str, job_def_name: str) -> str:
    return f'{workflow_uuid}-{job_def_name}'


def zip_workflow_variables(config: WorkflowDefinition) -> Generator[Variable, None, None]:
    for v in config.variables:
        yield v
    for job in config.job_definitions:
        for v in job.variables:
            yield v


def fill_variables(config: WorkflowDefinition,
                   variables: List[Variable],
                   *,
                   dry_run: bool = False) -> WorkflowDefinition:
    variables_mapper = {v.name: v for v in variables}
    for slot_variable in zip_workflow_variables(config):
        variable = variables_mapper.get(slot_variable.name)
        if variable is None:
            continue
        if variable.value_type != slot_variable.value_type:
            raise TypeError(f'unmatched variable type! {variable.value_type} != {slot_variable.value_type}')
        if dry_run:
            continue
        slot_variable.typed_value.MergeFrom(variable.typed_value)
        slot_variable.value = variable.value

    return config
