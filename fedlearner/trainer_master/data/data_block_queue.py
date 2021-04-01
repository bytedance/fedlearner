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

import logging
import threading


class DataBlockQueue:
    def __init__(self, epoch_num=1):
        self._mutex = threading.Lock()
        self._queue = list()
        self._size = 0
        self._next = 0
        self._num_outs = 0
        self._epoch_num = epoch_num  # <= 0 for endless

    def put(self, data_blocks):
        with self._mutex:
            self._queue.extend(data_blocks)
            self._size += len(data_blocks)

    def _empty(self):
        return self._size == 0 or \
               (self._epoch_num > 0 and
                self._num_outs == (self._epoch_num * self._size))

    def get(self):
        with self._mutex:
            if self._empty():
                return None
            self._next = self._next % self._size
            data = self._queue[self._next]
            self._next = self._next + 1
            self._num_outs += 1
            return data

    def empty(self):
        with self._mutex:
            return self._empty()
