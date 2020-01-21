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

class CustomizedOptions(object):
    def __init__(self):
        self._raw_data_iter = None
        self._example_joiner = None
        self._compressed_type = None

    def set_raw_data_iter(self, raw_data_iter):
        self._raw_data_iter = raw_data_iter

    def get_raw_data_iter(self):
        return self._raw_data_iter

    def set_example_joiner(self, exampel_joiner):
        self._example_joiner = exampel_joiner

    def get_example_joiner(self):
        return self._example_joiner

    def set_compressed_type(self, compressed_type):
        self._compressed_type = compressed_type

    def get_compressed_type(self):
        return self._compressed_type
