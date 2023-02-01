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

import json
import unittest
import os
import fsspec

from pyspark.sql.types import BinaryType, IntegerType, StructField, StructType, StringType
from error_code import JobException

from testing.spark_test_case import PySparkTestCase
from dataset_alignment import DatasetAlignment
from util import dataset_schema_path


class DatasetAlignmentTest(PySparkTestCase):

    def setUp(self) -> None:
        super().setUp()
        self._generate_tfrecords()

    def tearDown(self) -> None:
        self._clear_up()
        return super().tearDown()

    def _generate_tfrecords(self):
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
        df.repartition(3).write.format('tfrecords').option('compression', 'none').save(os.path.join(
            self.tmp_dataset_path, 'input_dataset/batch/batch_test'),
                                                                                       mode='overwrite')
        with fsspec.open(dataset_schema_path(os.path.join(self.tmp_dataset_path, 'input_dataset')), mode='w') as f:
            json.dump(df.schema.jsonValue(), f)

    def _clear_up(self):
        fs = fsspec.filesystem('file')
        if fs.isdir(self.tmp_dataset_path):
            fs.rm(self.tmp_dataset_path, recursive=True)

    def test_dataset_alignment(self):
        input_dataset_path = os.path.join(self.tmp_dataset_path, 'input_dataset')
        input_batch_path = os.path.join(input_dataset_path, 'batch/batch_test')
        wildcard = '**'
        output_dataset_path = os.path.join(self.tmp_dataset_path, 'output_dataset')
        output_batch_patch = os.path.join(output_dataset_path, 'batch/batch_test')
        input_schema_path = os.path.join(self.test_data, 'alignment_schema.json')
        output_error_path = os.path.join(output_dataset_path, 'errors/batch_test')
        with fsspec.open(input_schema_path, 'r') as f:
            json_schema = f.read()
        # test passed while no exception raise
        DatasetAlignment(self.spark, input_dataset_path, input_batch_path, wildcard, output_batch_patch, json_schema,
                         output_dataset_path, output_error_path).run()
        fs = fsspec.filesystem('file')
        self.assertFalse(fs.isdir(output_error_path))
        files = fs.ls(output_batch_patch)
        file_names = []
        for file in files:
            # skip Cyclic Redundancy Check file
            if file.endswith('.crc'):
                continue
            file_name = file.split('/')[-1]
            if file_name != '_SUCCESS':
                print(file_name)
                self.assertNotEqual(fs.size(file), 0)
            file_names.append(file_name)
        golden_file_names = ['part-r-00000', 'part-r-00001', 'part-r-00002', '_SUCCESS']
        self.assertCountEqual(file_names, golden_file_names)
        input_schema_path = dataset_schema_path(input_dataset_path)
        self.assertTrue(fs.isfile(input_schema_path))
        with fsspec.open(input_schema_path, 'r') as f:
            input_schema = f.read()
        output_schema_path = dataset_schema_path(output_dataset_path)
        self.assertTrue(fs.isfile(output_schema_path))
        with fsspec.open(output_schema_path, 'r') as f:
            output_schema = f.read()
        self.assertEqual(input_schema, output_schema)

    def test_dataset_alignment_error(self):
        input_dataset_path = os.path.join(self.tmp_dataset_path, 'input_dataset')
        input_batch_path = os.path.join(input_dataset_path, 'batch/batch_test')
        wildcard = '**'
        output_dataset_path = os.path.join(self.tmp_dataset_path, 'output_dataset')
        output_batch_patch = os.path.join(output_dataset_path, 'batch/batch_test')
        input_schema_path = os.path.join(self.test_data, 'alignment_schema_error.json')
        output_error_path = os.path.join(output_dataset_path, 'errors/batch_test')
        with fsspec.open(input_schema_path, 'r') as f:
            json_schema = f.read()
        # test passed while no exception raise
        with self.assertRaises(JobException):
            DatasetAlignment(self.spark, input_dataset_path, input_batch_path, wildcard, output_batch_patch,
                             json_schema, output_dataset_path, output_error_path).run()
        fs = fsspec.filesystem('file')
        self.assertTrue(fs.isdir(output_error_path))
        golden_data = [{
            'field': 'raw_id',
            'message': '3 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '8 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '10 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '4 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '6 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '7 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '9 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '1 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '2 is not of type \'string\''
        }, {
            'field': 'raw_id',
            'message': '5 is not of type \'string\''
        }]
        error_file = fs.glob(output_error_path + '/part-*.json')[0]
        error_msgs = []
        with fs.open(error_file) as f:
            for line in f:
                error_msgs.append(json.loads(line))
        self.assertCountEqual(error_msgs, golden_data)


if __name__ == '__main__':
    unittest.main()
