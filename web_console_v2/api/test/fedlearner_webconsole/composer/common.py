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

from fedlearner_webconsole.composer.interface import IItem, ItemType, IRunner
from fedlearner_webconsole.composer.models import RunnerStatus, Context


class Task(IItem):
    def __init__(self, task_id: int):
        self.id = task_id

    def type(self) -> ItemType:
        return ItemType.TASK

    def get_id(self) -> int:
        return self.id


# used in lambda
def _raise(ex):
    raise ex


def sleep_and_log(id: int, sec: int):
    time.sleep(sec)
    logging.info(f'id-{id}, sleep {sec}')


RunnerCases = [
    # normal: 1, 2, 3
    {
        'id': 1,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(1, 1) or (RunnerStatus.DONE, {})),
    },
    {
        'id': 2,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(2, 1) or (RunnerStatus.DONE, {})),
    },
    {
        'id': 3,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(3, 1) or (RunnerStatus.DONE, {})),
    },
    # failed: 4, 5, 6
    {
        'id': 4,
        'start': (lambda _: sleep_and_log(4, 5) and False),
        'result': (lambda _: (RunnerStatus.FAILED, {})),
    },
    {
        'id': 5,
        'start': (lambda _: _raise(TimeoutError)),
        'result': (lambda _: (RunnerStatus.FAILED, {})),
    },
    {
        'id': 6,
        'start': (lambda _: sleep_and_log(6, 10) and False),
        'result': (lambda _: (RunnerStatus.FAILED, {})),
    },
    # busy: 7, 8, 9
    {
        'id': 7,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(7, 15) or (RunnerStatus.DONE, {})),
    },
    {
        'id': 8,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(8, 15) or (RunnerStatus.DONE, {})),
    },
    {
        'id': 9,
        'start': (lambda _: True),
        'result': (lambda _: sleep_and_log(9, 15) or (RunnerStatus.DONE, {})),
    },
]


class TaskRunner(IRunner):
    def __init__(self, task_id: int):
        self.task_id = task_id

    def start(self, context: Context):
        logging.info(
            f"[mock_task_runner] {self.task_id} started, ctx: {context}")
        RunnerCases[self.task_id - 1]['start'](context)

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        result = RunnerCases[self.task_id - 1]['result'](context)
        logging.info(f"[mock_task_runner] {self.task_id} done result {result}")
        return result


class InputDirTaskRunner(IRunner):
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.input_dir = ''

    def start(self, context: Context):
        self.input_dir = context.data.get(str(self.task_id),
                                          {}).get('input_dir', '')
        logging.info(
            f'[mock_inputdir_task_runner] start, input_dir: {self.input_dir}')

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        s = {
            1: RunnerStatus.RUNNING,
            2: RunnerStatus.DONE,
            3: RunnerStatus.FAILED,
        }
        return s.get(self.task_id, RunnerStatus.RUNNING), {}