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
import logging
import sys

from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.dataset.batch_stats import BatchStatsRunner
from fedlearner_webconsole.dataset.scheduler.dataset_long_period_scheduler import DatasetLongPeriodScheduler
from fedlearner_webconsole.dataset.scheduler.dataset_short_period_scheduler import DatasetShortPeriodScheduler
from fedlearner_webconsole.job.scheduler import JobScheduler
from fedlearner_webconsole.project.project_scheduler import ScheduleProjectRunner
from fedlearner_webconsole.serving.runners import ModelSignatureParser, QueryParticipantStatusRunner, UpdateModelRunner
from fedlearner_webconsole.workflow.cronjob import WorkflowCronJob
from fedlearner_webconsole.workflow.workflow_scheduler import ScheduleWorkflowRunner
from fedlearner_webconsole.cleanup.cleaner_cronjob import CleanupCronJob
from fedlearner_webconsole.mmgr.cronjob import ModelTrainingCronJob
from fedlearner_webconsole.mmgr.scheduler import ModelJobSchedulerRunner, ModelJobGroupSchedulerRunner, \
    ModelJobGroupLongPeriodScheduler
from fedlearner_webconsole.tee.runners import TeeCreateRunner, TeeResourceCheckRunner


def global_runner_fn():
    # register runner_fn
    runner_fn = {
        ItemType.WORKFLOW_CRON_JOB.value: WorkflowCronJob,
        ItemType.BATCH_STATS.value: BatchStatsRunner,
        ItemType.SERVING_SERVICE_PARSE_SIGNATURE.value: ModelSignatureParser,
        ItemType.SERVING_SERVICE_QUERY_PARTICIPANT_STATUS.value: QueryParticipantStatusRunner,
        ItemType.SERVING_SERVICE_UPDATE_MODEL.value: UpdateModelRunner,
        ItemType.SCHEDULE_WORKFLOW.value: ScheduleWorkflowRunner,
        ItemType.SCHEDULE_JOB.value: JobScheduler,
        ItemType.CLEANUP_CRON_JOB.value: CleanupCronJob,
        ItemType.MODEL_TRAINING_CRON_JOB.value: ModelTrainingCronJob,
        ItemType.TEE_CREATE_RUNNER.value: TeeCreateRunner,
        ItemType.TEE_RESOURCE_CHECK_RUNNER.value: TeeResourceCheckRunner,
        ItemType.SCHEDULE_PROJECT.value: ScheduleProjectRunner,
        ItemType.DATASET_LONG_PERIOD_SCHEDULER.value: DatasetLongPeriodScheduler,
        ItemType.DATASET_SHORT_PERIOD_SCHEDULER.value: DatasetShortPeriodScheduler,
        ItemType.SCHEDULE_MODEL_JOB.value: ModelJobSchedulerRunner,
        ItemType.SCHEDULE_MODEL_JOB_GROUP.value: ModelJobGroupSchedulerRunner,
        ItemType.SCHEDULE_LONG_PERIOD_MODEL_JOB_GROUP.value: ModelJobGroupLongPeriodScheduler,
    }
    for item in ItemType:
        if item.value in runner_fn or item == ItemType.TASK:
            continue
        logging.error(f'failed to find item, {item.value}')
        sys.exit(-1)
    return runner_fn
