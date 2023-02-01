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
import threading
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Callable, Optional

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2


class ThreadReaper(object):

    def __init__(self, worker_num: int):
        """ThreadPool with battery

        Args:
            worker_num: the number of running threads to do jobs
        """
        self.lock = threading.RLock()
        self.worker_num = worker_num
        self.running_worker_num = 0
        self._running_workers = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=worker_num)

    def is_running(self, runner_id: int) -> bool:
        with self.lock:
            return runner_id in self._running_workers

    def submit(self,
               runner_id: int,
               fn: IRunnerV2,
               context: RunnerContext,
               done_callback: Optional[Callable[[int, Future], None]] = None) -> bool:
        if self.is_full():
            return False

        def full_done_callback(fu: Future):
            # The order matters, as we need to update the status at the last.
            if done_callback:
                done_callback(runner_id, fu)
            self._track_status(runner_id, fu)

        logging.info(f'[thread_reaper] enqueue {runner_id}')
        with self.lock:
            if runner_id in self._running_workers:
                logging.warning(f'f[thread_reaper] {runner_id} already enqueued')
                return False
            self.running_worker_num += 1
            self._running_workers[runner_id] = fn
            fu = self._thread_pool.submit(fn.run, context=context)
            fu.add_done_callback(full_done_callback)
        return True

    def _track_status(self, runner_id: int, fu: Future):
        with self.lock:
            self.running_worker_num -= 1
            # Safely removing
            self._running_workers.pop(runner_id, None)
            try:
                logging.info(f'f------Job {runner_id} is done------')
                logging.info(f'result: {fu.result()}')
            except Exception as e:  # pylint: disable=broad-except
                logging.info(f'error: {str(e)}')
            if self.running_worker_num < 0:
                logging.error(f'[thread_reaper] something wrong, should be non-negative, '
                              f'val: f{self.running_worker_num}')

    def is_full(self) -> bool:
        with self.lock:
            return self.worker_num == self.running_worker_num

    def stop(self, wait: bool):
        self._thread_pool.shutdown(wait=wait)
