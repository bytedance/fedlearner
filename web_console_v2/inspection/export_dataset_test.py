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

import argparse
import os
import fsspec
import unittest
from unittest.mock import MagicMock, patch

from pyspark import SparkConf

from export_dataset import get_args, export_dataset, export_dataset_for_unknown_type, export_dataset_for_structured_type
from testing.spark_test_case import PySparkTestCase
from util import FileFormat


class AnalyzerTest(PySparkTestCase):

    def test_get_args(self):
        data_path = '/data/fake_path'
        file_wildcard = 'batch/**/**'
        batch_name = '20220101'
        export_path = '/data/export'
        file_format_unknown = 'unknown'

        # test file_wildcard
        args = get_args([f'--data_path={data_path}', f'--file_wildcard={file_wildcard}', \
            f'--export_path={export_path}'])
        self.assertEqual(args.data_path, data_path)
        self.assertEqual(args.file_wildcard, file_wildcard)
        self.assertEqual(args.export_path, export_path)
        self.assertEqual(args.file_format, FileFormat.TFRECORDS)
        self.assertIsNone(args.batch_name)

        # test batch_name
        args = get_args([f'--data_path={data_path}', f'--batch_name={batch_name}', f'--export_path={export_path}', \
            f'--file_format={file_format_unknown}'])
        self.assertEqual(args.data_path, data_path)
        self.assertIsNone(args.file_wildcard)
        self.assertEqual(args.export_path, export_path)
        self.assertEqual(args.file_format, FileFormat.UNKNOWN)
        self.assertEqual(args.batch_name, batch_name)

    @patch('export_dataset.export_dataset_for_unknown_type')
    @patch('export_dataset.export_dataset_for_structured_type')
    @patch('export_dataset.get_args')
    def test_export_dataset(self, mock_get_args: MagicMock, mock_export_dataset_for_structured_type: MagicMock,
                            mock_export_dataset_for_unknown_type: MagicMock):
        data_path = '/data/fake_path'
        file_wildcard = 'batch/**/**'
        batch_name = '20220101'
        export_path = '/data/export/20220101'
        file_format_tf = 'tfrecords'
        file_format_unknown = 'unknown'

        # test use spark
        mock_get_args.return_value = argparse.Namespace(data_path=data_path,
                                                        file_wildcard=file_wildcard,
                                                        export_path=export_path,
                                                        batch_name=None,
                                                        file_format=file_format_tf)
        export_dataset()
        mock_export_dataset_for_structured_type.assert_called_once_with(input_path='/data/fake_path/batch/**/**',
                                                                        export_path='/data/export/20220101',
                                                                        file_format=FileFormat.TFRECORDS)
        mock_export_dataset_for_unknown_type.assert_not_called()

        mock_get_args.reset_mock()
        mock_export_dataset_for_structured_type.reset_mock()
        mock_export_dataset_for_unknown_type.reset_mock()

        # test use fsspec
        mock_get_args.return_value = argparse.Namespace(data_path=data_path,
                                                        export_path=export_path,
                                                        batch_name=batch_name,
                                                        file_format=file_format_unknown)
        export_dataset()
        mock_export_dataset_for_unknown_type.assert_called_once_with(input_path='/data/fake_path/batch/20220101',
                                                                     export_path='/data/export/20220101')
        mock_export_dataset_for_structured_type.assert_not_called()

    @patch('export_dataset.build_spark_conf')
    def test_export_dataset_for_structured_type(self, mock_build_spark_conf: MagicMock):
        # set local spark
        mock_build_spark_conf.return_value = SparkConf().setMaster('local')

        input_path = os.path.join(self.test_data, 'csv/medium_csv')
        export_path = self.tmp_dataset_path

        export_dataset_for_structured_type(input_path=input_path, export_path=export_path, file_format=FileFormat.CSV)
        fs = fsspec.filesystem('file')
        files = fs.ls(export_path)
        file_names = {f.split('/')[-1] for f in files}
        expect_file_names = {'_SUCCESS'}
        self.assertTrue(expect_file_names.issubset(file_names))

    def test_export_dataset_for_unknown_type(self):
        input_path = os.path.join(self.test_data, 'csv/medium_csv')
        export_path = self.tmp_dataset_path

        export_dataset_for_unknown_type(input_path=input_path, export_path=export_path)
        fs = fsspec.filesystem('file')
        files = fs.ls(export_path)
        file_names = {f.split('/')[-1] for f in files}
        expect_file_names = {'default_credit_hetero_guest.csv'}
        self.assertEqual(expect_file_names, file_names)


if __name__ == '__main__':
    unittest.main()
