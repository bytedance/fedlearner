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

# pylint: disable=protected-access
import unittest
import json
import os
from unittest import mock
import fsspec

from pyspark.sql.types import BinaryType, IntegerType, StructField, StructType, StringType

from testing.spark_test_case import PySparkTestCase
from analyzer.analyzer_task import AnalyzerTask
from dataset_directory import DatasetDirectory


class AnalyzerTaskTest(PySparkTestCase):

    def setUp(self) -> None:
        super().setUp()
        self._data_path = os.path.join(self.tmp_dataset_path, 'test_dataset')
        self._dataset_directory = DatasetDirectory(self._data_path)
        self._batch_name = 'test_batch'
        self._filesystem = fsspec.filesystem('file')
        self.maxDiff = None
        self.analyzer_task = AnalyzerTask()

    def tearDown(self) -> None:
        self._clear_up()
        return super().tearDown()

    def _generate_dataframe(self):
        data = [
            (1, b'01001100111', 256, 256, 3, 'cat', 'image_1'),
            (2, b'01001100111', 245, 246, None, 'dog', 'image_2'),
            (3, b'01001100111', None, 314, 3, 'cat', 'image_3'),
        ]
        schema = StructType([
            StructField('raw_id', IntegerType(), False),
            StructField('data', BinaryType(), False),
            StructField('rows', IntegerType(), True),
            StructField('cols', IntegerType(), False),
            StructField('channel', IntegerType(), True),
            StructField('label', StringType(), False),
            StructField('file_name', StringType(), False),
        ])
        return self.spark.createDataFrame(data=data, schema=schema)

    def _generate_all_string_and_binary_dataframe(self):
        data = [
            ('1', b'01001100111', 'cat'),
            ('2', b'01001100111', 'dog'),
            ('3', b'01001100111', 'cat'),
        ]
        schema = StructType([
            StructField('raw_id', StringType(), False),
            StructField('image', BinaryType(), False),
            StructField('label', StringType(), False),
        ])
        return self.spark.createDataFrame(data=data, schema=schema)

    def _generate_fake_image_dataframe(self):
        data = [
            (1, b'010011001110', 2, 2, 3, 'cat', 'image_1.jpg'),
            (2, b'010011', 1, 2, 3, 'dog', 'image_2.jpg'),
            (3, b'010011001110100111', 3, 2, 3, 'cat', 'image_3.jpg'),
        ]
        schema = StructType([
            StructField('raw_id', IntegerType(), False),
            StructField('data', BinaryType(), False),
            StructField('height', IntegerType(), False),
            StructField('width', IntegerType(), False),
            StructField('nChannels', IntegerType(), False),
            StructField('label', StringType(), False),
            StructField('file_name', StringType(), False),
        ])
        return self.spark.createDataFrame(data=data, schema=schema)

    def _generate_tfrecords_image(self):
        df = self._generate_fake_image_dataframe()
        df.repartition(3).write.format('tfrecords').option('compression', 'none').save(
            self._dataset_directory.batch_path(self._batch_name), mode='overwrite')
        with fsspec.open(self._dataset_directory.schema_file, mode='w') as f:
            json.dump(df.schema.jsonValue(), f)

    def _generate_tfrecords_tabular(self):
        data = [
            (1, 2, 2, 3, 'cat', 'image_1.jpg'),
            (2, 1, 2, 3, 'dog', 'image_2.jpg'),
            (3, 3, 2, 3, 'cat', 'image_3.jpg'),
        ]
        schema = StructType([
            StructField('raw_id', IntegerType(), False),
            StructField('height', IntegerType(), False),
            StructField('width', IntegerType(), False),
            StructField('nChannels', IntegerType(), False),
            StructField('label', StringType(), False),
            StructField('file_name', StringType(), False),
        ])
        df = self.spark.createDataFrame(data=data, schema=schema)
        df.repartition(3).write.format('tfrecords').option('compression', 'none').save(
            self._dataset_directory.batch_path(self._batch_name), mode='overwrite')
        with fsspec.open(self._dataset_directory.schema_file, mode='w') as f:
            json.dump(df.schema.jsonValue(), f)

    def _clear_up(self):
        if self._filesystem.isdir(self.tmp_dataset_path):
            self._filesystem.rm(self.tmp_dataset_path, recursive=True)

    def test_analyzer_image(self):
        self._generate_tfrecords_image()
        self.analyzer_task.run(spark=self.spark,
                               dataset_path=self._data_path,
                               wildcard='batch/test_batch/**',
                               is_image=True,
                               batch_name=self._batch_name,
                               buckets_num=10,
                               thumbnail_path=self._dataset_directory.thumbnails_path(self._batch_name))
        expected_meta = {
            'dtypes': [{
                'key': 'raw_id',
                'value': 'int'
            }, {
                'key': 'height',
                'value': 'int'
            }, {
                'key': 'width',
                'value': 'int'
            }, {
                'key': 'nChannels',
                'value': 'int'
            }, {
                'key': 'label',
                'value': 'string'
            }, {
                'key': 'file_name',
                'value': 'string'
            }],
            'label_count': mock.ANY,
            'count': 3,
            'sample': mock.ANY,
            'features': {
                'raw_id': {
                    'count': '3',
                    'mean': '2.0',
                    'stddev': '1.0',
                    'min': '1',
                    'max': '3',
                    'missing_count': '0'
                },
                'height': {
                    'count': '3',
                    'mean': '2.0',
                    'stddev': '1.0',
                    'min': '1',
                    'max': '3',
                    'missing_count': '0'
                },
                'width': {
                    'count': '3',
                    'mean': '2.0',
                    'stddev': '0.0',
                    'min': '2',
                    'max': '2',
                    'missing_count': '0'
                },
                'nChannels': {
                    'count': '3',
                    'mean': '3.0',
                    'stddev': '0.0',
                    'min': '3',
                    'max': '3',
                    'missing_count': '0'
                },
                'label': {
                    'count': '3',
                    'mean': None,
                    'stddev': None,
                    'min': 'cat',
                    'max': 'dog',
                    'missing_count': '0'
                },
                'file_name': {
                    'count': '3',
                    'mean': None,
                    'stddev': None,
                    'min': 'image_1.jpg',
                    'max': 'image_3.jpg',
                    'missing_count': '0'
                }
            },
            'hist': {
                'raw_id': {
                    'x': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8, 3.0],
                    'y': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1]
                },
                'height': {
                    'x': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8, 3.0],
                    'y': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1]
                },
                'width': {
                    'x': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
                    'y': [0, 0, 0, 0, 0, 0, 0, 0, 0, 3]
                },
                'nChannels': {
                    'x': [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
                    'y': [0, 0, 0, 0, 0, 0, 0, 0, 0, 3]
                }
            }
        }
        expected_sample = [[1, 2, 2, 3, 'cat', 'image_1.jpg'], [2, 1, 2, 3, 'dog', 'image_2.jpg'],
                           [3, 3, 2, 3, 'cat', 'image_3.jpg']]
        expected_label_count = [{'label': 'dog', 'count': 1}, {'label': 'cat', 'count': 2}]
        expected_file_names = ['image_1.png', 'image_2.png', 'image_3.png']
        files = self._filesystem.ls(self._dataset_directory.thumbnails_path(self._batch_name))
        file_names = [f.split('/')[-1] for f in files]
        self.assertCountEqual(file_names, expected_file_names)
        batch_level_meta_path = self._dataset_directory.batch_meta_file(batch_name=self._batch_name)
        self.assertTrue(self._filesystem.isfile(batch_level_meta_path))
        with fsspec.open(batch_level_meta_path, 'r') as f:
            batch_level_meta = json.load(f)
        self.assertEqual(batch_level_meta, expected_meta)
        self.assertCountEqual(batch_level_meta.get('sample'), expected_sample)
        self.assertCountEqual(batch_level_meta.get('label_count'), expected_label_count)

    def test_analyzer_tabular(self):
        self._generate_tfrecords_tabular()
        self.analyzer_task.run(spark=self.spark,
                               dataset_path=self._data_path,
                               wildcard='batch/test_batch/**',
                               is_image=False,
                               batch_name=self._batch_name,
                               buckets_num=10,
                               thumbnail_path=self._dataset_directory.thumbnails_path(self._batch_name))
        expected_meta = {
            'dtypes': [{
                'key': 'raw_id',
                'value': 'int'
            }, {
                'key': 'height',
                'value': 'int'
            }, {
                'key': 'width',
                'value': 'int'
            }, {
                'key': 'nChannels',
                'value': 'int'
            }, {
                'key': 'label',
                'value': 'string'
            }, {
                'key': 'file_name',
                'value': 'string'
            }],
            'count': 3,
            'sample': mock.ANY,
            'features': {
                'raw_id': {
                    'count': '3',
                    'mean': '2.0',
                    'stddev': '1.0',
                    'min': '1',
                    'max': '3',
                    'missing_count': '0'
                },
                'height': {
                    'count': '3',
                    'mean': '2.0',
                    'stddev': '1.0',
                    'min': '1',
                    'max': '3',
                    'missing_count': '0'
                },
                'width': {
                    'count': '3',
                    'mean': '2.0',
                    'stddev': '0.0',
                    'min': '2',
                    'max': '2',
                    'missing_count': '0'
                },
                'nChannels': {
                    'count': '3',
                    'mean': '3.0',
                    'stddev': '0.0',
                    'min': '3',
                    'max': '3',
                    'missing_count': '0'
                },
                'label': {
                    'count': '3',
                    'mean': None,
                    'stddev': None,
                    'min': 'cat',
                    'max': 'dog',
                    'missing_count': '0'
                },
                'file_name': {
                    'count': '3',
                    'mean': None,
                    'stddev': None,
                    'min': 'image_1.jpg',
                    'max': 'image_3.jpg',
                    'missing_count': '0'
                }
            },
            'hist': {
                'raw_id': {
                    'x': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8, 3.0],
                    'y': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1]
                },
                'height': {
                    'x': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8, 3.0],
                    'y': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1]
                },
                'width': {
                    'x': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
                    'y': [0, 0, 0, 0, 0, 0, 0, 0, 0, 3]
                },
                'nChannels': {
                    'x': [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
                    'y': [0, 0, 0, 0, 0, 0, 0, 0, 0, 3]
                }
            }
        }
        batch_level_meta_path = self._dataset_directory.batch_meta_file(batch_name=self._batch_name)
        self.assertTrue(self._filesystem.isfile(batch_level_meta_path))
        with fsspec.open(batch_level_meta_path, 'r') as f:
            batch_level_meta = json.load(f)
        self.assertEqual(batch_level_meta, expected_meta)
        expected_sample = [[1, 2, 2, 3, 'cat', 'image_1.jpg'], [2, 1, 2, 3, 'dog', 'image_2.jpg'],
                           [3, 3, 2, 3, 'cat', 'image_3.jpg']]
        self.assertCountEqual(batch_level_meta.get('sample'), expected_sample)

    def test_extract_feature_hist(self):
        df = self._generate_dataframe()
        hist = self.analyzer_task._extract_feature_hist(self.spark, df, dict(df.dtypes), 10)
        expect_hist = {
            'raw_id': {
                'x': [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8, 3.0],
                'y': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1]
            },
            'rows': {
                'x': [
                    0.0, 25.6, 51.2, 76.80000000000001, 102.4, 128.0, 153.60000000000002, 179.20000000000002, 204.8,
                    230.4, 256.0
                ],
                'y': [1, 0, 0, 0, 0, 0, 0, 0, 0, 2]
            },
            'cols': {
                'x': [246.0, 252.8, 259.6, 266.4, 273.2, 280.0, 286.8, 293.6, 300.4, 307.2, 314.0],
                'y': [1, 1, 0, 0, 0, 0, 0, 0, 0, 1]
            },
            'channel': {
                'x': [
                    0.0, 0.3, 0.6, 0.8999999999999999, 1.2, 1.5, 1.7999999999999998, 2.1, 2.4, 2.6999999999999997, 3.0
                ],
                'y': [1, 0, 0, 0, 0, 0, 0, 0, 0, 2]
            }
        }
        self.assertDictEqual(hist, expect_hist)

        # this case is special designed for a corner case:
        # if the input data column are all string/binary, hist should be empty
        df = self._generate_all_string_and_binary_dataframe()
        hist = self.analyzer_task._extract_feature_hist(self.spark, df, dict(df.dtypes), 10)
        self.assertDictEqual(hist, {})

    def test_extract_thumbnail(self):
        df = self._generate_fake_image_dataframe()
        self.analyzer_task._extract_thumbnail(df, self._dataset_directory.thumbnails_path(self._batch_name))
        files = self._filesystem.ls(self._dataset_directory.thumbnails_path(self._batch_name))
        file_names = [f.split('/')[-1] for f in files]
        golden_file_names = ['image_1.png', 'image_2.png', 'image_3.png']
        self.assertCountEqual(file_names, golden_file_names)

    def test_extract_feature_metrics(self):
        df = self._generate_dataframe()
        df_stats_dict = self.analyzer_task._extract_feature_metrics(df, dict(df.dtypes))
        expect_stats_dict = {
            'raw_id': {
                'count': '3',
                'mean': '2.0',
                'stddev': '1.0',
                'min': '1',
                'max': '3',
                'missing_count': '0'
            },
            'rows': {
                'count': '2',
                'mean': '250.5',
                'stddev': mock.ANY,
                'min': '245',
                'max': '256',
                'missing_count': '1'
            },
            'cols': {
                'count': '3',
                'mean': '272.0',
                'stddev': mock.ANY,
                'min': '246',
                'max': '314',
                'missing_count': '0'
            },
            'channel': {
                'count': '2',
                'mean': '3.0',
                'stddev': '0.0',
                'min': '3',
                'max': '3',
                'missing_count': '1'
            },
            'label': {
                'count': '3',
                'mean': None,
                'stddev': None,
                'min': 'cat',
                'max': 'dog',
                'missing_count': '0'
            },
            'file_name': {
                'count': '3',
                'mean': None,
                'stddev': None,
                'min': 'image_1',
                'max': 'image_3',
                'missing_count': '0'
            }
        }
        self.assertDictEqual(df_stats_dict, expect_stats_dict)

    def test_extract_metadata_image(self):
        df = self._generate_fake_image_dataframe()
        meta = self.analyzer_task._extract_metadata(df, True)
        expect_meta = {
            'dtypes': [{
                'key': 'raw_id',
                'value': 'int'
            }, {
                'key': 'height',
                'value': 'int'
            }, {
                'key': 'width',
                'value': 'int'
            }, {
                'key': 'nChannels',
                'value': 'int'
            }, {
                'key': 'label',
                'value': 'string'
            }, {
                'key': 'file_name',
                'value': 'string'
            }],
            'label_count': [{
                'label': 'dog',
                'count': 1
            }, {
                'label': 'cat',
                'count': 2
            }],
            'count':
                3,
            'sample': [[1, 2, 2, 3, 'cat', 'image_1.jpg'], [2, 1, 2, 3, 'dog', 'image_2.jpg'],
                       [3, 3, 2, 3, 'cat', 'image_3.jpg']]
        }
        self.assertEqual(meta, expect_meta)

    def test_extract_metadata_tabular(self):
        df = self._generate_dataframe()
        meta = self.analyzer_task._extract_metadata(df, False)
        expect_meta = {
            'dtypes': [{
                'key': 'raw_id',
                'value': 'int'
            }, {
                'key': 'data',
                'value': 'binary'
            }, {
                'key': 'rows',
                'value': 'int'
            }, {
                'key': 'cols',
                'value': 'int'
            }, {
                'key': 'channel',
                'value': 'int'
            }, {
                'key': 'label',
                'value': 'string'
            }, {
                'key': 'file_name',
                'value': 'string'
            }],
            'count':
                3,
            'sample': [[1, bytearray(b'01001100111'), 256, 256, 3, 'cat', 'image_1'],
                       [2, bytearray(b'01001100111'), 245, 246, None, 'dog', 'image_2'],
                       [3, bytearray(b'01001100111'), None, 314, 3, 'cat', 'image_3']]
        }
        self.assertEqual(meta, expect_meta)

    def test_empty_file(self):
        batch_path = self._dataset_directory.batch_path(self._batch_name)
        fs = fsspec.get_mapper(batch_path).fs
        fs.mkdir(batch_path)
        fs.touch(os.path.join(batch_path, 'empty_file'))
        self.analyzer_task.run(spark=self.spark,
                               dataset_path=self._data_path,
                               wildcard='batch/test_batch/**',
                               is_image=False,
                               batch_name=self._batch_name,
                               buckets_num=10,
                               thumbnail_path=self._dataset_directory.thumbnails_path(self._batch_name))
        meta_path = self._dataset_directory.batch_meta_file(batch_name=self._batch_name)
        self.assertFalse(self._filesystem.exists(meta_path))


if __name__ == '__main__':
    unittest.main()
