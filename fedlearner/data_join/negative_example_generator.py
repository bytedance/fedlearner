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

class NegativeExampleGenerator(object):
    def __init__(self, negative_sampling_rate):
        self._buf = {}
        self._negative_sampling_rate = negative_sampling_rate
        self._field_name = ["label", "type"]
        self._field_value = [0, 0]

    def update(self, mismatches):
        self._buf.update(mismatches)

    def _skip(self):
        if random.random() <= self._negative_sampling_rate:
            return False
        return True

    def generate(self, follower_item, prev_leader_idx, leader_idx):
        for idx in range(prev_leader_idx, leader_idx):
            if self._skip():
                continue
            if idx not in self._buf:
                continue
            example_id = self._buf[idx].example_id
            if isinstance(example_id, bytes):
                example_id = example_id.decode()
            event_time = self._buf[idx].event_time
            example = type(follower_item).make(example_id, event_time,
                                               example_id, self._field_name,
                                               self._field_value)
            yield example, idx, 0
            del self._buf[idx]

        del_keys = [k for k in self._buf if k < prev_leader_idx]
        for k in del_keys:
            del self._buf[k]
