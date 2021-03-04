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
import random
from fedlearner.data_join.join_expr.expression import Expr

class NegativeExampleGenerator(object):
    def __init__(self, negative_sampling_rate, filter_expr=None):
        """Args
            filter_expr: i.e. et(label, 1), select the sample from leader
            meeting label=1
        """
        self._buf = {}
        #FIXME  prev_index should be assigned to the leader restart
        # index after restart.
        self._prev_index = 0
        self._negative_sampling_rate = negative_sampling_rate
        self._field_name = ["label", "joined"]
        self._field_value = [0, 0]
        if filter_expr and len(filter_expr.strip()) > 0:
            self._filter_expr = Expr(filter_expr)
        else:
            self._filter_expr = None

    def update(self, mismatches):
        self._buf.update(mismatches)

    def _skip(self, idx):
        filtered = True
        if self._filter_expr and \
           not self._filter_expr.run_func(0)(self._buf[idx], None):
            filtered = False
        if filtered and random.random() <= self._negative_sampling_rate:
            return False
        return True

    def generate(self, item, leader_idx):
        for idx in range(self._prev_index, leader_idx):
            if idx not in self._buf:
                continue
            if self._skip(idx):
                continue
            example_id = self._buf[idx].example_id
            event_time = self._buf[idx].event_time
            example = type(item).make(example_id, event_time,
                                      None, self._field_name,
                                      self._field_value)
            yield example, idx, 0
            del self._buf[idx]

        for k, v in list(self._buf.items()):
            if k < self._prev_index:
                del self._buf[k]
        if leader_idx > self._prev_index:
            self._prev_index = leader_idx
