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
import os
import fsspec

from testing.spark_test_case import PySparkTestCase
from pyspark.sql.types import IntegerType, StructField, StructType, StringType, LongType, DoubleType
from pyspark.sql.dataframe import DataFrame

from dataset_format_checker import check_format, JobException
from dataset_directory import DatasetDirectory
from util import FileFormat, load_by_file_format


class FormatCheckerTest(PySparkTestCase):

    def setUp(self) -> None:
        super().setUp()
        self._data_path = os.path.join(self.tmp_dataset_path, 'test_dataset')
        self._dataset_directory = DatasetDirectory(self._data_path)
        self._batch_name = 'test_batch'
        self.maxDiff = None

    def tearDown(self) -> None:
        fs = fsspec.filesystem('file')
        if fs.isdir(self._data_path):
            fs.rm(self._data_path, recursive=True)
        return super().tearDown()

    def _generate_tfrecords_tabular(self) -> DataFrame:
        data = [
            (1, 2, 2, 3, 'cat', 'image_1.jpg', 3.21),
            (2, 1, 2, 3, 'dog', 'image_2.jpg', 3.23),
            (3, 3, 2, 3, 'cat', 'image_3.jpg', 3.26),
        ]
        schema = StructType([
            StructField('example_id', IntegerType(), False),
            StructField('height', LongType(), False),
            StructField('width', IntegerType(), False),
            StructField('nChannels', IntegerType(), False),
            StructField('label', StringType(), False),
            StructField('file_name', StringType(), False),
            StructField('score', DoubleType(), False),
        ])
        return self.spark.createDataFrame(data=data, schema=schema)

    def _generate_tfrecords_tabular_duplicate_raw_id(self) -> DataFrame:
        data = [
            (1, 2, 2, 3, 3.21),
            (1, 1, 2, 3, 3.23),
            (3, 3, 2, 3, 3.26),
        ]
        schema = StructType([
            StructField('raw_id', IntegerType(), False),
            StructField('height', LongType(), False),
            StructField('width', IntegerType(), False),
            StructField('nChannels', IntegerType(), False),
            StructField('score', DoubleType(), False),
        ])
        return self.spark.createDataFrame(data=data, schema=schema)

    def test_format_checker(self):
        # check succeeded
        input_batch_path = os.path.join(self.test_data, 'csv/medium_csv')
        file_format = FileFormat.CSV
        checkers = ['RAW_ID_CHECKER', 'NUMERIC_COLUMNS_CHECKER']
        df = load_by_file_format(self.spark, input_batch_path, file_format)
        check_format(df, checkers)

    def test_no_raw_id(self):
        df = self._generate_tfrecords_tabular()
        checkers = ['RAW_ID_CHECKER']
        with self.assertRaises(JobException):
            check_format(df, checkers)

    def test_duplicated_raw_id(self):
        df = self._generate_tfrecords_tabular_duplicate_raw_id()
        checkers = ['RAW_ID_CHECKER']
        with self.assertRaises(JobException):
            check_format(df, checkers)

    def test_numeric_check_failed(self):
        df = self._generate_tfrecords_tabular()
        checkers = ['NUMERIC_COLUMNS_CHECKER']
        with self.assertRaises(JobException):
            check_format(df, checkers)


if __name__ == '__main__':
    unittest.main()
