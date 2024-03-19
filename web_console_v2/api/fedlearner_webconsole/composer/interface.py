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

from abc import ABCMeta, abstractmethod

import enum
from typing import Tuple

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.models import RunnerStatus

from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput


# NOTE: remember to register new item in `global_runner_fn` \
# which defined in `runner.py`
class ItemType(enum.Enum):
    TASK = 'task'  # test only
    WORKFLOW_CRON_JOB = 'workflow_cron_job'  # v2
    BATCH_STATS = 'batch_stats'  # v2
    SERVING_SERVICE_PARSE_SIGNATURE = 'serving_service_parse_signature'  # v2
    SERVING_SERVICE_QUERY_PARTICIPANT_STATUS = 'serving_service_query_participant_status'  # v2
    SERVING_SERVICE_UPDATE_MODEL = 'serving_service_update_model'  # v2
    SCHEDULE_WORKFLOW = 'schedule_workflow'  # v2
    SCHEDULE_JOB = 'schedule_job'  # v2
    CLEANUP_CRON_JOB = 'cleanup_cron_job'  # v2
    MODEL_TRAINING_CRON_JOB = 'model_training_cron_job'  # v2
    TEE_CREATE_RUNNER = 'tee_create_runner'  # v2
    TEE_RESOURCE_CHECK_RUNNER = 'tee_resource_check_runner'  # v2
    SCHEDULE_PROJECT = 'schedule_project'  # v2
    DATASET_LONG_PERIOD_SCHEDULER = 'dataset_long_period_scheduler'  # v2
    DATASET_SHORT_PERIOD_SCHEDULER = 'dataset_short_period_scheduler'  # v2
    SCHEDULE_MODEL_JOB = 'schedule_model_job'  # v2
    SCHEDULE_MODEL_JOB_GROUP = 'schedule_model_job_group'  # v2
    SCHEDULE_LONG_PERIOD_MODEL_JOB_GROUP = 'schedule_long_period_model_job_group'  # v2


# item interface
class IItem(metaclass=ABCMeta):

    @abstractmethod
    def type(self) -> ItemType:
        pass

    @abstractmethod
    def get_id(self) -> int:
        pass


class IRunnerV2(metaclass=ABCMeta):

    @abstractmethod
    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        """Runs the runner.

        The implementation should be light, as runners will be executed by `ThreadPoolExecutor`.

        Args:
            context: immutable context in the runner.
        Returns:
            status and the output.
        """
