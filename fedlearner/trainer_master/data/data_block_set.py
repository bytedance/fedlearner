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


class DataBlockSet(object):
    '''
        For quick implement a prototype, use python Queue,
        If data size is laregr than local memory,
        replace by Redis or other distributed Store.
    '''

    def __init__(self, maxsize=0):
        self._db_set = {}

    def add(self, data_block):
        if data_block.block_id:
            self._db_set[data_block.block_id] = data_block

    def get(self, block_id):
        logging.debug("search %s and result: %r", block_id,
                      block_id in self._db_set)
        return self._db_set.pop(block_id, None)

    def __str__(self):
        ret = ""
        for item in self._db_set:
            ret += str(item) + ","
        return ret
