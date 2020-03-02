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

try:
    import queue
except ImportError:
    import Queue as queue


class DataBlockQueue(object):
    '''
        For quick implement a prototype, use python Queue,
        If data size is laregr than local memory, replace by Redis
        or other distributed Store.
    '''
    def __init__(self, maxsize=0):
        self._db_queue = queue.Queue(maxsize=maxsize)

    def put(self, data_block):
        self._db_queue.put(data_block)

    def get(self):
        return self._db_queue.get(block=True, timeout=5)

    def empty(self):
        return self._db_queue.empty()
