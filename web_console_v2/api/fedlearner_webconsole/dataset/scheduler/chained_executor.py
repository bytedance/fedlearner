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

import logging

from fedlearner_webconsole.dataset.scheduler.consts import ExecutorType, ExecutorResult
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.cron_dataset_job_executor import CronDatasetJobExecutor
from fedlearner_webconsole.dataset.scheduler.update_auth_status_executor import UpdateAuthStatusExecutor
from fedlearner_webconsole.dataset.scheduler.dataset_job_executor import DatasetJobExecutor
from fedlearner_webconsole.dataset.scheduler.pending_dataset_job_stage_executor import PendingDatasetJobStageExecutor
from fedlearner_webconsole.dataset.scheduler.running_dataset_job_stage_executor import RunningDatasetJobStageExecutor
from fedlearner_webconsole.proto.composer_pb2 import ExecutorResults


def _get_executor(executor_type: ExecutorType) -> BaseExecutor:
    executor_map = {
        ExecutorType.CRON_DATASET_JOB: CronDatasetJobExecutor,
        ExecutorType.UPDATE_AUTH_STATUS: UpdateAuthStatusExecutor,
        ExecutorType.DATASET_JOB: DatasetJobExecutor,
        ExecutorType.PENDING_DATASET_JOB_STAGE: PendingDatasetJobStageExecutor,
        ExecutorType.RUNNING_DATASET_JOB_STAGE: RunningDatasetJobStageExecutor,
    }
    return executor_map.get(executor_type)()


def run_executor(executor_type: ExecutorType) -> ExecutorResults:
    executor = _get_executor(executor_type=executor_type)
    item_ids = executor.get_item_ids()
    succeeded_items = []
    failed_items = []
    skip_items = []
    for item_id in item_ids:
        try:
            executor_result = executor.run_item(item_id=item_id)
            if executor_result == ExecutorResult.SUCCEEDED:
                succeeded_items.append(item_id)
            elif executor_result == ExecutorResult.FAILED:
                failed_items.append(item_id)
            else:
                skip_items.append(item_id)
        except Exception as e:  # pylint: disable=broad-except
            logging.exception(f'[Dataset ChainedExecutor] failed to run {item_id}, executor_type: {executor_type.name}')
            failed_items.append(item_id)
    return ExecutorResults(succeeded_item_ids=succeeded_items, failed_item_ids=failed_items, skip_item_ids=skip_items)
