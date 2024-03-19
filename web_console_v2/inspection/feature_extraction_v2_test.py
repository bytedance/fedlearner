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
import unittest

from cityhash import CityHash64  # pylint: disable=no-name-in-module

from testing.spark_test_case import PySparkTestCase
from dataset_directory import DatasetDirectory
from feature_extraction_v2 import feature_extraction, FileFormat
from util import EXAMPLE_ID


class FeatureExtractionV2Test(PySparkTestCase):

    def test_feature_extract(self):
        part_num = 3
        file_format = FileFormat.CSV
        dataset_dir = DatasetDirectory(self.tmp_dataset_path)
        batch_name = '20220331-1200'
        side_output_path = dataset_dir.side_output_path(batch_name)
        raw_data_path = os.path.join(side_output_path, 'raw')
        joined_data_path = os.path.join(side_output_path, 'joined')
        output_batch_path = dataset_dir.batch_path(batch_name)
        # test no data
        os.makedirs(joined_data_path, exist_ok=True)
        feature_extraction(self.spark,
                           original_data_path=raw_data_path,
                           joined_data_path=joined_data_path,
                           part_num=part_num,
                           part_key='raw_id',
                           file_format=file_format,
                           output_file_format=FileFormat.CSV,
                           output_batch_name=batch_name,
                           output_dataset_path=self.tmp_dataset_path)
        self.assertTrue(os.path.exists(output_batch_path))
        # write raw data
        data = [(str(i), f'x{str(i)}', i + 1) for i in range(1000)]
        df = self.spark.createDataFrame(data=data, schema=['raw_id', 'name', 'age'])
        df.write.format(file_format.value).option('compression', 'none').option('header', 'true').save(raw_data_path,
                                                                                                       mode='overwrite')
        # write joined id
        joined_id = [(str(i)) for i in range(0, 1000, 4)]
        os.makedirs(joined_data_path, exist_ok=True)
        expected_ids_list = []
        for part_id in range(part_num):
            expected_ids_list.append([i for i in joined_id if CityHash64(i) % part_num == part_id])
            with open(os.path.join(joined_data_path, f'partition_{part_id}'), 'w', encoding='utf-8') as f:
                f.write('raw_id\n')
                f.write('\n'.join(expected_ids_list[part_id]))

        feature_extraction(self.spark,
                           original_data_path=raw_data_path,
                           joined_data_path=joined_data_path,
                           part_num=part_num,
                           part_key='raw_id',
                           file_format=file_format,
                           output_file_format=FileFormat.CSV,
                           output_batch_name=batch_name,
                           output_dataset_path=self.tmp_dataset_path)
        # check raw_id and example_id from extracted data
        filenames = list(filter(lambda file: file.startswith('part'), sorted(os.listdir(output_batch_path))))
        for part_id, file in enumerate(filenames):
            with open(os.path.join(output_batch_path, file), 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.assertEqual([row['raw_id'] for row in reader], sorted(expected_ids_list[part_id]))
            with open(os.path.join(output_batch_path, file), 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.assertEqual([row[EXAMPLE_ID] for row in reader], sorted(expected_ids_list[part_id]))


if __name__ == '__main__':
    unittest.main()
