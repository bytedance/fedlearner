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

from abc import ABCMeta, abstractmethod

import enum
from typing import Tuple

from fedlearner_webconsole.composer.models import Context, RunnerStatus


class ItemType(enum.Enum):
    TASK = 'task'
    MEMORY = 'memory'
    WORKFLOW_CRON_JOB = 'workflow_cron_job'


# item interface
class IItem(metaclass=ABCMeta):
    @abstractmethod
    def type(self) -> ItemType:
        pass

    @abstractmethod
    def get_id(self) -> int:
        pass


# runner interface
class IRunner(metaclass=ABCMeta):
    @abstractmethod
    def start(self, context: Context):
        pass

    @abstractmethod
    def stop(self, context: Context):
        pass

    @abstractmethod
    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        pass

    @abstractmethod
    def timeout(self) -> int:
        # TODO: if this runner is timeout, should be stopped
        pass
