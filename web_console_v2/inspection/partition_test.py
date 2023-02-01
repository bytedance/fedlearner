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

import os
import csv
import shutil
import unittest
import tempfile

from cityhash import CityHash64  # pylint: disable=no-name-in-module

from testing.spark_test_case import PySparkTestCase
from dataset_directory import DatasetDirectory
from partition import partition, FileFormat


class FeatureExtractionV2Test(PySparkTestCase):

    def test_partition(self):
        part_num = 3
        file_format = FileFormat.CSV
        data = [(str(i), f'x{str(i)}', i + 1) for i in range(1000)]
        df = self.spark.createDataFrame(data=data, schema=['raw_id', 'name', 'age'])
        expected_ids_list = []
        for part_id in range(part_num):
            expected_ids_list.append([d[0] for d in data if CityHash64(d[0]) % part_num == part_id])
        # test write raw data
        with tempfile.TemporaryDirectory() as input_path:
            df.write.format(file_format.value).option('header', 'true').save(input_path, mode='overwrite')
            dataset_dir = DatasetDirectory(self.tmp_dataset_path)
            batch_name = '20220331-1200'
            side_output_path = dataset_dir.side_output_path(batch_name)
            partition(spark=self.spark,
                      input_path=input_path,
                      file_format=file_format,
                      output_file_format=FileFormat.CSV,
                      output_dir=side_output_path,
                      part_num=part_num,
                      part_key='raw_id',
                      write_raw_data=True)
        raw_data_path = os.path.join(side_output_path, 'raw')
        filenames = list(filter(lambda file: file.startswith('part'), sorted(os.listdir(raw_data_path))))
        for part_id, file in enumerate(filenames):
            with open(os.path.join(raw_data_path, file), 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.assertEqual(sorted([row['raw_id'] for row in reader]), sorted(expected_ids_list[part_id]))
        ids_data_path = os.path.join(side_output_path, 'ids')
        filenames = list(filter(lambda file: file.startswith('part'), sorted(os.listdir(ids_data_path))))
        for part_id, file in enumerate(filenames):
            with open(os.path.join(ids_data_path, file), 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.assertEqual(sorted([row['raw_id'] for row in reader]), sorted(expected_ids_list[part_id]))
        shutil.rmtree(self.tmp_dataset_path)
        # test not write raw data
        with tempfile.TemporaryDirectory() as input_path:
            df.write.format(file_format.value).option('header', 'true').save(input_path, mode='overwrite')
            dataset_dir = DatasetDirectory(self.tmp_dataset_path)
            batch_name = '20220331-1200'
            side_output_path = dataset_dir.side_output_path(batch_name)
            partition(spark=self.spark,
                      input_path=input_path,
                      file_format=file_format,
                      output_file_format=FileFormat.CSV,
                      output_dir=side_output_path,
                      part_num=part_num,
                      part_key='raw_id',
                      write_raw_data=False)
        raw_data_path = os.path.join(side_output_path, 'raw')
        self.assertFalse(os.path.exists(raw_data_path))
        shutil.rmtree(self.tmp_dataset_path)
        # test no data
        with tempfile.TemporaryDirectory() as input_path:
            dataset_dir = DatasetDirectory(self.tmp_dataset_path)
            batch_name = '20220331-1200'
            side_output_path = dataset_dir.side_output_path(batch_name)
            partition(spark=self.spark,
                      input_path=input_path,
                      file_format=file_format,
                      output_file_format=FileFormat.CSV,
                      output_dir=side_output_path,
                      part_num=part_num,
                      part_key='raw_id',
                      write_raw_data=True)
        raw_data_path = os.path.join(side_output_path, 'raw')
        self.assertTrue(os.path.exists(raw_data_path))
        ids_data_path = os.path.join(side_output_path, 'ids')
        self.assertTrue(os.path.exists(ids_data_path))
        shutil.rmtree(self.tmp_dataset_path)


if __name__ == '__main__':
    unittest.main()
