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
import unittest
from unittest.mock import ANY, MagicMock, patch

from pyspark import SparkConf

from analyzer_v2 import get_args, analyzer
from error_code import AreaCode, ErrorType, JobException


class AnalyzerTest(unittest.TestCase):

    def test_get_args(self):
        data_path = '/data/fake_path'
        file_wildcard = 'batch/**/**'
        buckets_num = '10'
        thumbnail_path = 'thumbnail'
        batch_name = '20220101'

        # test image
        args = get_args(['image', f'--data_path={data_path}', f'--file_wildcard={file_wildcard}', \
            f'--buckets_num={buckets_num}', f'--thumbnail_path={thumbnail_path}', '--skip', \
            f'--batch_name={batch_name}'])
        self.assertEqual(args.command, 'image')
        self.assertEqual(args.data_path, data_path)
        self.assertEqual(args.file_wildcard, file_wildcard)
        self.assertEqual(args.buckets_num, int(buckets_num))
        self.assertEqual(args.thumbnail_path, thumbnail_path)
        self.assertTrue(args.skip)
        self.assertEqual(args.batch_name, batch_name)

        # test tabular
        args = get_args(['tabular', f'--data_path={data_path}', f'--file_wildcard={file_wildcard}', \
            f'--buckets_num={buckets_num}', f'--thumbnail_path={thumbnail_path}', f'--batch_name={batch_name}'])
        self.assertEqual(args.command, 'tabular')
        self.assertEqual(args.data_path, data_path)
        self.assertEqual(args.file_wildcard, file_wildcard)
        self.assertEqual(args.buckets_num, int(buckets_num))
        self.assertFalse(args.skip)
        self.assertEqual(args.batch_name, batch_name)

        # test none_structured
        args = get_args(['none_structured', '--skip'])
        self.assertEqual(args.command, 'none_structured')
        self.assertTrue(args.skip)

        # test no required args
        with self.assertRaises(SystemExit):
            get_args(['image', '--skip'])

    @patch('analyzer_v2.write_termination_message')
    @patch('analyzer_v2.get_args')
    @patch('analyzer_v2.build_spark_conf')
    @patch('analyzer_v2.AnalyzerTask.run')
    def test_analyzer(self, mock_run: MagicMock, mock_build_spark_conf: MagicMock, mock_get_args: MagicMock,
                      mock_write_termination_message: MagicMock):
        # set local spark
        mock_build_spark_conf.return_value = SparkConf().setMaster('local')

        # test skip
        mock_get_args.return_value = argparse.Namespace(skip=True)
        analyzer()
        mock_build_spark_conf.assert_not_called()

        # test no batch_name
        mock_get_args.reset_mock()
        data_path = '/data/fake_path'
        file_wildcard = 'batch/**/**'
        buckets_num = 10
        thumbnail_path = 'thumbnail'
        mock_get_args.return_value = argparse.Namespace(command='image',
                                                        data_path=data_path,
                                                        file_wildcard=file_wildcard,
                                                        buckets_num=buckets_num,
                                                        batch_name='',
                                                        thumbnail_path=thumbnail_path,
                                                        skip=False)
        with self.assertRaises(JobException):
            analyzer()
            mock_write_termination_message.assert_called_once_with(AreaCode.ANALYZER, ErrorType.INPUT_PARAMS_ERROR,
                                                                   'failed to find batch_name')

        # test not skip
        mock_get_args.reset_mock()
        batch_name = '20220101'
        mock_get_args.return_value = argparse.Namespace(command='image',
                                                        data_path=data_path,
                                                        file_wildcard=file_wildcard,
                                                        buckets_num=buckets_num,
                                                        batch_name=batch_name,
                                                        thumbnail_path=thumbnail_path,
                                                        skip=False)
        analyzer()
        mock_run.assert_called_once_with(spark=ANY,
                                         dataset_path='file://' + data_path,
                                         wildcard=file_wildcard,
                                         is_image=True,
                                         batch_name=batch_name,
                                         buckets_num=buckets_num,
                                         thumbnail_path=thumbnail_path)


if __name__ == '__main__':
    unittest.main()
