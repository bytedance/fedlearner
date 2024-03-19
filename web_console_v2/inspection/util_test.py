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
import fsspec
import os
import json

from util import FileFormat, dataset_schema_path, load_tfrecords, is_file_matched, load_by_file_format, \
    normalize_file_path
from pyspark.sql.types import BinaryType, IntegerType, StructField, StructType, StringType
from testing.spark_test_case import PySparkTestCase


class UtilTest(PySparkTestCase):

    def tearDown(self) -> None:
        self._clear_up()
        return super().tearDown()

    def _generate_tfrecords_with_schema(self, dataset_path: str, batch_path: str):
        data = [
            (1, b'01001100111', 256, 256, 3, 'cat'),
            (2, b'01001100111', 244, 246, 3, 'dog'),
            (3, b'01001100111', 255, 312, 3, 'cat'),
            (4, b'01001100111', 256, 255, 3, 'cat'),
            (5, b'01001100111', 201, 241, 3, 'cat'),
            (6, b'01001100111', 255, 221, 3, 'dog'),
            (7, b'01001100111', 201, 276, 3, 'dog'),
            (8, b'01001100111', 258, 261, 3, 'dog'),
            (9, b'01001100111', 198, 194, 3, 'cat'),
            (10, b'01001100111', 231, 221, 3, 'cat'),
        ]
        schema = StructType([
            StructField('raw_id', IntegerType(), False),
            StructField('image', BinaryType(), False),
            StructField('rows', IntegerType(), False),
            StructField('cols', IntegerType(), False),
            StructField('channel', IntegerType(), False),
            StructField('label', StringType(), False),
        ])
        df = self.spark.createDataFrame(data=data, schema=schema)
        df.repartition(3).write.format('tfrecords').option('compression', 'none').save(batch_path, mode='overwrite')
        with fsspec.open(dataset_schema_path(dataset_path), mode='w') as f:
            json.dump(df.schema.jsonValue(), f)

    def _generate_tfrecords_no_schema(self, batch_path: str):
        data = [
            (1, b'01001100111', 256, 256, 3, 'cat'),
            (2, b'01001100111', 244, 246, 3, 'dog'),
            (3, b'01001100111', 255, 312, 3, 'cat'),
            (4, b'01001100111', 256, 255, 3, 'cat'),
            (5, b'01001100111', 201, 241, 3, 'cat'),
            (6, b'01001100111', 255, 221, 3, 'dog'),
            (7, b'01001100111', 201, 276, 3, 'dog'),
            (8, b'01001100111', 258, 261, 3, 'dog'),
            (9, b'01001100111', 198, 194, 3, 'cat'),
            (10, b'01001100111', 231, 221, 3, 'cat'),
        ]
        df = self.spark.createDataFrame(data=data)
        df.repartition(3).write.format('tfrecords').option('compression', 'none').save(batch_path, mode='overwrite')

    def _clear_up(self):
        fs = fsspec.filesystem('file')
        if fs.isdir(self.tmp_dataset_path):
            fs.rm(self.tmp_dataset_path, recursive=True)

    def test_load_tfrecords_with_schema(self):
        dataset_path = os.path.join(self.tmp_dataset_path, 'input_dataset')
        batch_path = os.path.join(dataset_path, 'batch/batch_test')
        self._generate_tfrecords_with_schema(dataset_path, batch_path)
        df = load_tfrecords(spark=self.spark, files=batch_path, dataset_path=dataset_path)
        data = [
            (1, b'01001100111', 256, 256, 3, 'cat'),
            (2, b'01001100111', 244, 246, 3, 'dog'),
            (3, b'01001100111', 255, 312, 3, 'cat'),
            (4, b'01001100111', 256, 255, 3, 'cat'),
            (5, b'01001100111', 201, 241, 3, 'cat'),
            (6, b'01001100111', 255, 221, 3, 'dog'),
            (7, b'01001100111', 201, 276, 3, 'dog'),
            (8, b'01001100111', 258, 261, 3, 'dog'),
            (9, b'01001100111', 198, 194, 3, 'cat'),
            (10, b'01001100111', 231, 221, 3, 'cat'),
        ]
        schema = StructType([
            StructField('raw_id', IntegerType(), False),
            StructField('image', BinaryType(), False),
            StructField('rows', IntegerType(), False),
            StructField('cols', IntegerType(), False),
            StructField('channel', IntegerType(), False),
            StructField('label', StringType(), False),
        ])
        expect_df = self.spark.createDataFrame(data=data, schema=schema)
        self.assertCountEqual(df.select('*').collect(), expect_df.select('*').collect())

    def test_load_tfrecords_no_schema(self):
        dataset_path = os.path.join(self.tmp_dataset_path, 'input_dataset')
        batch_path = os.path.join(dataset_path, 'batch/batch_test')
        self._generate_tfrecords_no_schema(batch_path)
        df = load_tfrecords(spark=self.spark, files=batch_path, dataset_path=dataset_path)
        expect_data = [
            set([1, '01001100111', 256, 256, 3, 'cat']),
            set([2, '01001100111', 244, 246, 3, 'dog']),
            set([3, '01001100111', 255, 312, 3, 'cat']),
            set([4, '01001100111', 256, 255, 3, 'cat']),
            set([5, '01001100111', 201, 241, 3, 'cat']),
            set([6, '01001100111', 255, 221, 3, 'dog']),
            set([7, '01001100111', 201, 276, 3, 'dog']),
            set([8, '01001100111', 258, 261, 3, 'dog']),
            set([9, '01001100111', 198, 194, 3, 'cat']),
            set([10, '01001100111', 231, 221, 3, 'cat']),
        ]
        data = []
        for row in df.select('*').collect():
            row_data = []
            for key, value in row.asDict().items():
                row_data.append(value)
            data.append(set(row_data))
        self.assertCountEqual(data, expect_data)

    def test_is_file_matched(self):
        dataset_path = os.path.join(self.tmp_dataset_path, 'input_dataset')
        batch_path = os.path.join(dataset_path, 'batch/batch_test')
        # test no data
        os.makedirs(batch_path, exist_ok=True)
        fs: fsspec.AbstractFileSystem = fsspec.get_mapper(dataset_path).fs
        fs.touch(os.path.join(batch_path, '_SUCCESS'))
        fs.touch(os.path.join(batch_path, 'part-0000._SUCCESS'))
        fs.touch(os.path.join(batch_path, 'part-0001._SUCCESS'))
        self.assertFalse(is_file_matched(batch_path))

        self._generate_tfrecords_with_schema(dataset_path, batch_path)
        self.assertTrue(is_file_matched(batch_path))
        batch_path_csv = os.path.join(batch_path, '*.csv')
        self.assertFalse(is_file_matched(batch_path_csv))
        batch_path_all = os.path.join(batch_path, '**')
        self.assertTrue(is_file_matched(batch_path_all))

    def test_load_by_file_format_csv(self):
        dataset_path = os.path.join(self.test_data, 'csv/small_csv')
        df = load_by_file_format(spark=self.spark, input_batch_path=dataset_path, file_format=FileFormat.CSV)
        expect_dtypes = [('example_id', 'int'), ('raw_id', 'int'), ('event_time', 'int'), ('x0', 'double'),
                         ('x1', 'double'), ('x2', 'double'), ('label', 'string')]
        self.assertCountEqual(expect_dtypes, df.dtypes)
        expect_data = [
            [1, 1, 20210621, -1.13672, 0.810161, 0.185828, 'cat'],
            [2, 2, 20210621, -0.365981, 0.810161, 0.185828, 'dog'],
            [3, 3, 20210621, -0.597202, 0.810161, 0.185828, 'frog'],
            [4, 4, 20210621, -0.905498, 0.810161, 0.185828, 'cat'],
            [5, 5, 20210621, -0.905498, -1.234323, 0.185828, 'dog'],
        ]
        data = []
        for row in df.select('*').collect():
            row_data = []
            for key, _ in expect_dtypes:
                row_data.append(row.asDict().get(key))
            data.append(row_data)
        self.assertCountEqual(data, expect_data)

    def test_load_by_file_format_tfrecords(self):
        dataset_path = os.path.join(self.test_data, 'tfrecords/small_tfrecords')
        df = load_by_file_format(spark=self.spark, input_batch_path=dataset_path, file_format=FileFormat.TFRECORDS)
        expect_dtypes = [('example_id', 'bigint'), ('raw_id', 'bigint'), ('event_time', 'bigint'), ('label', 'string')]
        self.assertCountEqual(expect_dtypes, df.dtypes)
        expect_data = [
            [1, 1, 20210621, 'cat'],
            [2, 2, 20210621, 'dog'],
            [3, 3, 20210621, 'frog'],
            [4, 4, 20210621, 'cat'],
            [5, 5, 20210621, 'dog'],
        ]
        data = []
        for row in df.select('*').collect():
            row_data = []
            for key, _ in expect_dtypes:
                row_data.append(row.asDict().get(key))
            data.append(row_data)
        self.assertCountEqual(data, expect_data)

    def test_load_by_file_format_failed(self):
        dataset_path = os.path.join(self.tmp_dataset_path, 'input_dataset')
        batch_path = os.path.join(dataset_path, 'batch/batch_test')
        with self.assertRaises(ValueError):
            load_by_file_format(spark=self.spark, input_batch_path=batch_path, file_format='unknown')

    def test_normalize_file_path(self):
        path = normalize_file_path('')
        self.assertEqual(path, '')

        path = normalize_file_path('/')
        self.assertEqual(path, 'file:///')

        path = normalize_file_path('/test/123')
        self.assertEqual(path, 'file:///test/123')

        path = normalize_file_path('test/123')
        self.assertEqual(path, 'test/123')

        path = normalize_file_path('hdfs:///test/123')
        self.assertEqual(path, 'hdfs:///test/123')


if __name__ == '__main__':
    unittest.main()
