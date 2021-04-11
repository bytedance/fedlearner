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

import random


def random_shuffle(data, chunk_size=0):
    data_size = len(data)
    if data_size == 0:
        return
    if chunk_size <= 0 or chunk_size >= data_size:
        chunk_size = data_size
    for start_idx in range(0, data_size, chunk_size):
        end_idx = min(start_idx + chunk_size, data_size)
        for i in range(start_idx+1, end_idx):
            j = random.randrange(start_idx, i)
            data[i], data[j] = data[j], data[i]
