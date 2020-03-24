# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

import threading
import logging
import time

class RoutineWorker(object):
    def __init__(self, name, routine_fn, cond_fn, exec_interval=None):
        self._name = name
        self._stop = False
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._exec_interval = exec_interval
        if self._exec_interval is not None and self._exec_interval <= 0:
            raise ValueError('exec interval: {} is illegal'.format(
                              exec_interval))
        self._cond_fn = cond_fn
        self._routine_fn = routine_fn
        self._skip_round = False
        self._thread = None
        self._args = tuple()
        self._kwargs = dict()

    def start_routine(self):
        with self._lock:
            if self._thread is not None:
                raise Exception('worker {} has started'.format(self._name))
            if self._stop:
                raise Exception('worker {} has stopped'.format(self._name))
            self._thread = threading.Thread(target=self._routine,
                                            name=self._name)
            self._thread.start()

    def stop_routine(self):
        tmp_th = None
        with self._lock:
            if self._thread is not None and not self._stop:
                self._stop = True
                self._condition.notify()
                tmp_th = self._thread
                self._thread = None
        if tmp_th is not None:
            tmp_th.join()

    def is_stopped(self):
        with self._lock:
            return self._stop

    def wakeup(self):
        with self._condition:
            self._condition.notify()
            self._skip_round = False

    def setup_args(self, *args, **kwargs):
        with self._lock:
            self._args = args
            self._kwargs = kwargs

    def obtain_args(self):
        with self._lock:
            args = self._args
            kwargs = self._kwargs
            self._args = tuple()
            self._kwargs = dict()
            return args, kwargs

    def _routine(self):
        exec_round = 0
        while not self.is_stopped():
            start_timepoint = time.time()
            while self._wait_for_exec():
                with self._lock:
                    if self._stop:
                        return
                    if self._exec_interval is None:
                        self._condition.wait()
                    else:
                        time_to_wait = (self._exec_interval -
                                        (time.time() - start_timepoint))
                        if time_to_wait > 0:
                            self._condition.wait(time_to_wait)
                        else:
                            self._skip_round = False
                            start_timepoint = time.time()
            try:
                with self._lock:
                    self._skip_round = self._exec_interval is not None
                args, kwargs = self.obtain_args()
                self._routine_fn(*args, **kwargs)
            except Exception as e: # pylint: disable=broad-except
                logging.error("worker: %s run %d rounds with exception: %s",
                              self._name, exec_round, e)
            else:
                logging.info("worker: %s exec %d round", self._name, exec_round)
            exec_round += 1
        logging.warning("worker %s will stop", self._name)

    def _wait_for_exec(self):
        with self._lock:
            if self._skip_round:
                return True
        return not self._cond_fn()
