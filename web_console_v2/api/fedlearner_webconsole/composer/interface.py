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


# NOTE: remember to register new item in `global_runner_fn` \
# which defined in `runner.py`
class ItemType(enum.Enum):
    TASK = 'task'  # test only
    MEMORY = 'memory'
    WORKFLOW_CRON_JOB = 'workflow_cron_job'
    DATA_PIPELINE = 'data_pipeline'


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
        """Start runner

        Args:
            context: shared in runner. Don't write data to context in this
            method. Only can read data via `context.data`.
        """

    @abstractmethod
    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        """Check runner result

        NOTE: You could check runner if is timeout in this method. If it's
            timeout, return `RunnerStatus.FAILED`. Since runners executed by
            `ThreadPoolExecutor` may have some common resources, it's better to
            stop the runner by user instead of `composer`.

        Args:
            context: shared in runner. In this method, data can be
               read or written to context via `context.data`.
        """
