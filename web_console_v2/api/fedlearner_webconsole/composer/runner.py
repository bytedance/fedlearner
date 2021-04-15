# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import time
from typing import Tuple

from fedlearner_webconsole.composer.interface import IItem, IRunner, ItemType
from fedlearner_webconsole.composer.models import Context, RunnerStatus, \
    SchedulerRunner
from fedlearner_webconsole.db import get_session
from fedlearner_webconsole.workflow.cronjob import WorkflowCronJob


class MemoryItem(IItem):
    def __init__(self, task_id: int):
        self.id = task_id

    def type(self) -> ItemType:
        return ItemType.MEMORY

    def get_id(self) -> int:
        return self.id


class MemoryRunner(IRunner):
    def __init__(self, task_id: int):
        """Runner Example

        Args:
             task_id: required
        """
        self.task_id = task_id

    def start(self, context: Context):
        # NOTE: in this method, context.data can only be getter,
        # don't modify context
        data = context.data.get(str(self.task_id), 'EMPTY')
        logging.info(f'[memory_runner] {self.task_id} started, data: {data}')

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        time.sleep(2)
        # use `get_session` to query database
        with get_session(context.db_engine) as session:
            count = session.query(SchedulerRunner).count()
            # write data to context
            context.set_data(f'is_done_{self.task_id}', {
                'status': 'OK',
                'count': count
            })
        return RunnerStatus.DONE, {}

    def stop(self, context: Context):
        logging.info(f'[memory_runner] {self.task_id} stopped, ctx: {context}')

    def timeout(self) -> int:
        return 60


# register runner_fn
global_runner_fn = {
    ItemType.MEMORY.value: MemoryRunner,
    ItemType.WORKFLOW_CRON_JOB.value: WorkflowCronJob,
}
