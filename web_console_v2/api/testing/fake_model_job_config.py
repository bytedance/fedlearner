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

from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.mmgr.models import ModelJobType
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, JobDefinition
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, ModelJobConfig


def get_workflow_config(model_job_type: ModelJobType):
    if model_job_type == ModelJobType.TRAINING:
        job_type = JobDefinition.JobType.TREE_MODEL_TRAINING
        mode = 'train'
    else:
        job_type = JobDefinition.JobType.TREE_MODEL_EVALUATION
        mode = 'eval'
    return WorkflowDefinition(job_definitions=[
        JobDefinition(name='train-job',
                      job_type=job_type,
                      variables=[
                          make_variable(name='mode', typed_value=mode),
                          Variable(name='data_source'),
                          Variable(name='data_path'),
                          Variable(name='file_wildcard'),
                      ],
                      yaml_template='{}')
    ])


def get_global_config() -> ModelJobGlobalConfig:
    global_config = ModelJobGlobalConfig(dataset_uuid='uuid', model_uuid='model-uuid')
    config = ModelJobConfig()
    config.variables.extend(
        [Variable(name='max_iters', typed_value=Value(number_value=4), value_type=Variable.ValueType.NUMBER)])
    global_config.global_config['test'].MergeFrom(config)
    config = ModelJobConfig()
    config.variables.extend([
        Variable(name='max_iters', typed_value=Value(number_value=4), value_type=Variable.ValueType.NUMBER),
        Variable(name='worker_cpu', typed_value=Value(string_value='2000m'), value_type=Variable.ValueType.STRING)
    ])
    global_config.global_config['peer'].MergeFrom(config)
    return global_config
