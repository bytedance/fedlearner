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

import os
import time
import unittest
import logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


from fedlearner.data_join.common import InputPathUtil


class TestCommon(unittest.TestCase):
    def test_input_path_util(self):
        base_dir = "/foo/bar"
        self.assertEqual(base_dir, InputPathUtil.format_path(base_dir))
        raw_base_dir = "oss://fff?key=value" + base_dir
        self.assertEqual(base_dir, InputPathUtil.format_path(raw_base_dir))
        raw_base_dir = "hdfs://foo/" + base_dir
        self.assertEqual(raw_base_dir, InputPathUtil.format_path(raw_base_dir))

