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
from uuid import uuid4

from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.job.models import JobType


def get_job_path(storage_root_path: str, job_name: str) -> str:
    return os.path.join(storage_root_path, 'job_output', job_name)


def get_exported_model_path(job_path: str) -> str:
    return os.path.join(job_path, 'exported_models')


def get_checkpoint_path(job_path: str) -> str:
    return os.path.join(job_path, 'checkpoints')


def get_output_path(job_path: str) -> str:
    return os.path.join(job_path, 'outputs')


def exported_model_version_path(exported_models_path, version: int):
    return os.path.join(exported_models_path, str(version))


def get_model_path(storage_root_path: str, uuid: str) -> str:
    return os.path.join(storage_root_path, 'model_output', uuid)


def build_workflow_name(model_job_type: str, algorithm_type: str, model_job_name: str) -> str:
    prefix = f'{model_job_type.lower()}-{algorithm_type.lower()}-{model_job_name}'
    # since the length of workflow name is limited to 255, the length of prefix should be less than 249
    return f'{prefix[:249]}-{uuid4().hex[:5]}'


def is_model_job(job_type: JobType):
    return job_type in [
        JobType.NN_MODEL_TRANINING, JobType.NN_MODEL_EVALUATION, JobType.TREE_MODEL_TRAINING,
        JobType.TREE_MODEL_EVALUATION
    ]


def deleted_name(name: str):
    """Rename the deleted model job, model, group due to unique constraint on name"""
    timestamp = now().strftime('%Y%m%d_%H%M%S')
    return f'deleted_at_{timestamp}_{name}'
