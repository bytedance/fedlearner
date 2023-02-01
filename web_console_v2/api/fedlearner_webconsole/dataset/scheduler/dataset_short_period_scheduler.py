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

from typing import Tuple

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.dataset.scheduler.chained_executor import run_executor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorType
from fedlearner_webconsole.proto.composer_pb2 import DatasetSchedulerOutput, RunnerOutput


class DatasetShortPeriodScheduler(IRunnerV2):

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        runner_output = RunnerOutput(dataset_scheduler_output=DatasetSchedulerOutput())

        executor_result = run_executor(executor_type=ExecutorType.DATASET_JOB)
        runner_output.dataset_scheduler_output.executor_outputs[ExecutorType.DATASET_JOB.value].MergeFrom(
            executor_result)

        executor_result = run_executor(executor_type=ExecutorType.PENDING_DATASET_JOB_STAGE)
        runner_output.dataset_scheduler_output.executor_outputs[ExecutorType.PENDING_DATASET_JOB_STAGE.value].MergeFrom(
            executor_result)

        executor_result = run_executor(executor_type=ExecutorType.RUNNING_DATASET_JOB_STAGE)
        runner_output.dataset_scheduler_output.executor_outputs[ExecutorType.RUNNING_DATASET_JOB_STAGE.value].MergeFrom(
            executor_result)

        return RunnerStatus.DONE, runner_output
