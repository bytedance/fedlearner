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
import threading
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor

from fedlearner_webconsole.composer.models import Context
from fedlearner_webconsole.composer.interface import IRunner


class ThreadReaper(object):
    def __init__(self, worker_num: int):
        """ThreadPool with battery

        Args:
            worker_num: the number of running threads to do jobs
        """
        self.lock = threading.RLock()
        self.worker_num = worker_num
        self.running_worker_num = 0
        self._thread_pool = ThreadPoolExecutor(max_workers=worker_num)

    def enqueue(self, name: str, timeout: int, fn: IRunner,
                context: Context) -> bool:
        if self.is_full():
            return False
        logging.info(f'[thread_reaper] enqueue {name}')
        with self.lock:
            self.running_worker_num += 1
            if timeout > -1:
                fu = self._thread_pool.submit(fn.start,
                                              context=context,
                                              timeout=timeout)
                fu.add_done_callback(self._track_status)
            else:  # no timeout limit
                fu = self._thread_pool.submit(fn.start, context=context)
                fu.add_done_callback(self._track_status)
        return True

    def _track_status(self, fu: Future):
        with self.lock:
            self.running_worker_num -= 1
            logging.info(f'this job is done, result: {fu.result()}')
            if self.running_worker_num < 0:
                logging.error(
                    f'[thread_reaper] something wrong, should be non-negative, '
                    f'val: f{self.running_worker_num}')

    def is_full(self) -> bool:
        with self.lock:
            return self.worker_num == self.running_worker_num

    def stop(self, wait: bool):
        self._thread_pool.shutdown(wait=wait)
