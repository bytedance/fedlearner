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
import json

from pyspark.sql.dataframe import DataFrame
from pyspark.sql import functions as spark_func
from pyspark.sql.types import StringType, StructType, Row

from testing.spark_test_case import PySparkTestCase

from converter_v2 import convert_image, convert_no_copy, convert_tabular
from dataset_directory import DatasetDirectory
from util import FileFormat, dataset_schema_path, load_tfrecords


@spark_func.udf(StringType())
def get_file_basename(origin_name: str) -> str:
    return os.path.basename(origin_name)


class ConverterTest(PySparkTestCase):

    def tearDown(self) -> None:
        self._clear_up()
        return super().tearDown()

    def _clear_up(self):
        fs = fsspec.filesystem('file')
        if fs.isdir(self.tmp_dataset_path):
            fs.rm(self.tmp_dataset_path, recursive=True)

    def assertDataframeEqual(self, df1: DataFrame, df2: DataFrame):
        self.assertEqual(df1.subtract(df2).count(), 0)
        self.assertEqual(df2.subtract(df1).count(), 0)

    def test_convert_image(self):
        input_batch_path = os.path.join(self.test_data, 'image')
        output_dataset_path = os.path.join(self.tmp_dataset_path, 'output_dataset')
        batch_name = 'batch_test'
        output_batch_path = DatasetDirectory(output_dataset_path).batch_path(batch_name)
        manifest_name = 'manifest.json'
        images_dir_name = 'images'
        convert_image(self.spark, output_dataset_path, output_batch_path, input_batch_path, manifest_name,
                      images_dir_name)
        fs = fsspec.filesystem('file')
        files = fs.ls(output_batch_path)
        file_names = {f.split('/')[-1] for f in files}
        expect_file_names = {'part-r-00000', 'part-r-00001', 'part-r-00002', '_SUCCESS'}
        self.assertTrue(expect_file_names.issubset(file_names))
        with fsspec.open(dataset_schema_path(output_dataset_path), 'r') as f:
            output_schema = json.load(f)
        expect_schema = {
            'type':
                'struct',
            'fields': [{
                'name': 'file_name',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'width',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'height',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'nChannels',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'mode',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'data',
                'type': 'binary',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'name',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'created_at',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'caption',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'label',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }]
        }
        self.assertEqual(output_schema, expect_schema)
        image_df = self.spark.read.format('image').load(os.path.join(input_batch_path, images_dir_name))
        converter_df = load_tfrecords(self.spark, output_batch_path, output_dataset_path)
        self.assertDataframeEqual(image_df.select('image.data'), converter_df.select('data'))
        converter_struct_df = converter_df.select('file_name', 'width', 'height', 'nChannels', 'mode', 'name',
                                                  'created_at', 'caption', 'label')
        expect_struct = [
            Row(file_name='000000005756.jpg',
                width=640,
                height=361,
                nChannels=3,
                mode=16,
                name='000000005756.jpg',
                created_at='2021-08-30T16:52:15.501516',
                caption='A group of people holding umbrellas looking at graffiti.',
                label='A'),
            Row(file_name='000000018425.jpg',
                width=640,
                height=480,
                nChannels=3,
                mode=16,
                name='000000018425.jpg',
                created_at='2021-08-30T16:52:15.501516',
                caption='Two giraffe grazing on tree leaves under a hazy sky.',
                label='B'),
            Row(file_name='000000008181.jpg',
                width=640,
                height=480,
                nChannels=3,
                mode=16,
                name='000000008181.jpg',
                created_at='2021-08-30T16:52:15.501516',
                caption='A motorcycle is parked on a gravel lot',
                label='C')
        ]
        self.assertCountEqual(converter_struct_df.collect(), expect_struct)

    def test_convert_tabular(self):
        input_batch_path = os.path.join(self.test_data, 'csv/medium_csv')
        output_dataset_path = os.path.join(self.tmp_dataset_path, 'output_dataset')
        batch_name = 'batch_test'
        output_batch_path = DatasetDirectory(output_dataset_path).batch_path(batch_name)
        file_format = FileFormat.CSV
        convert_tabular(self.spark, output_dataset_path, output_batch_path, input_batch_path, file_format)
        fs = fsspec.filesystem('file')
        files = fs.ls(output_batch_path)
        file_names = {f.split('/')[-1] for f in files}
        expect_file_names = {'part-r-00000', '_SUCCESS'}
        self.assertTrue(expect_file_names.issubset(file_names))
        with fsspec.open(dataset_schema_path(output_dataset_path), 'r') as f:
            output_schema = json.load(f)
        expect_schema = {
            'type':
                'struct',
            'fields': [{
                'name': 'example_id',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'raw_id',
                'type': 'string',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'event_time',
                'type': 'integer',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x0',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x1',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x2',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x3',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x4',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x5',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x6',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x7',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x8',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }, {
                'name': 'x9',
                'type': 'double',
                'nullable': True,
                'metadata': {}
            }]
        }
        self.assertEqual(output_schema, expect_schema)
        raw_df = self.spark.read.format('csv').option('header', 'true').schema(
            StructType.fromJson(expect_schema)).load(input_batch_path)
        converter_df = load_tfrecords(self.spark, output_batch_path, output_dataset_path)
        self.assertEqual(raw_df.schema, converter_df.schema)
        # TODO(liuhehan): add df content check
        self.assertEqual(raw_df.count(), converter_df.count())

    def test_convert_empty(self):
        input_batch_path = os.path.join(self.test_data, 'csv/*.fake')
        output_dataset_path = os.path.join(self.tmp_dataset_path, 'output_dataset')
        batch_name = 'batch_test'
        output_batch_path = DatasetDirectory(output_dataset_path).batch_path(batch_name)
        file_format = FileFormat.CSV
        convert_tabular(self.spark, output_dataset_path, output_batch_path, input_batch_path, file_format)
        self.assertTrue(fsspec.get_mapper(output_batch_path).fs.isdir(output_batch_path))

    def test_converter_no_copy(self):
        input_batch_path = os.path.join(self.test_data, 'csv/medium_csv')
        output_dataset_path = os.path.join(self.tmp_dataset_path, 'output_dataset')
        batch_name = 'batch_test'
        output_batch_path = DatasetDirectory(output_dataset_path).batch_path(batch_name)
        convert_no_copy(output_dataset_path, output_batch_path, input_batch_path)
        with fsspec.open(DatasetDirectory(output_dataset_path).source_batch_path_file(batch_name), 'r') as f:
            self.assertEqual(f.read(), input_batch_path)


if __name__ == '__main__':
    unittest.main()
