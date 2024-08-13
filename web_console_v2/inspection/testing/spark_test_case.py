# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import unittest
import tempfile
import os
from pathlib import Path

from pyspark import SparkConf
from pyspark.sql import SparkSession


class PySparkTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Uses threads to run spark
        # Ref: https://spark.apache.org/docs/latest/submitting-applications.html#master-urls
        conf = SparkConf().setMaster('local[*]').setAppName('test')
        cls.spark = SparkSession.builder.config(conf=conf).getOrCreate()
        cls.tmp_dataset_path = os.path.join(tempfile.gettempdir(), 'tmp_data')
        cls.test_data = str(Path(__file__, '../test_data').resolve())

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()
