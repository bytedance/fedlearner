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

class _CustomizedOptions(object):
    def __init__(self):
        self.use_mock_etcd = False
        self.raw_data_iter = None
        self.example_joiner = None
        self.compressed_type = None

global_options = _CustomizedOptions()

def set_use_mock_etcd():
    global_options.use_mock_etcd = True

def get_use_mock_etcd():
    return global_options.use_mock_etcd

def set_raw_data_iter(raw_data_iter):
    global_options.raw_data_iter = raw_data_iter

def get_raw_data_iter():
    return global_options.raw_data_iter

def set_example_joiner(exampel_joiner):
    global_options.example_joiner = exampel_joiner

def get_example_joiner():
    return global_options.example_joiner

def set_compressed_type(compressed_type):
    global_options.compressed_type = compressed_type

def get_compressed_type():
    return global_options.compressed_type
