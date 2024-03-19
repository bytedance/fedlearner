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

from abc import ABC, abstractmethod

from sqlalchemy import func
from sqlalchemy.orm import Session

from fedlearner_webconsole.composer.models import SchedulerItem, SchedulerRunner, RunnerStatus


class RunnerStrategy(ABC):

    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def should_run(self, item: SchedulerItem) -> bool:
        """Checks if the scheduler item should run or not."""


class SingletonStrategy(RunnerStrategy):
    """A strategy to make sure there is only one runner instance for the scheduler item.

    1. For normal scheduler item, there is no difference with normal strategy.
    2. For cron jobs, there will be only one scheduler runner for the item.
    """

    def should_run(self, item: SchedulerItem) -> bool:
        if not item.need_run():
            return False

        if item.cron_config:
            ongoing_count = self.session.query(func.count(SchedulerRunner.id)).filter(
                SchedulerRunner.item_id == item.id,
                SchedulerRunner.status.in_([RunnerStatus.INIT.value, RunnerStatus.RUNNING.value])).scalar()
            if ongoing_count > 0:
                return False

        return True
