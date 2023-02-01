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

from dataset_directory import DatasetDirectory


class UtilTest(unittest.TestCase):
    _DATASET_PATH = '/fakepath/test_dataset'
    _BATCH_NAME = 'test_batch_name'

    def setUp(self) -> None:
        super().setUp()
        self._dataset_dir = DatasetDirectory(dataset_path=self._DATASET_PATH)

    def test_dataset_path(self):
        self.assertEqual(self._dataset_dir.dataset_path, self._DATASET_PATH)

    def test_batch_path(self):
        self.assertEqual(self._dataset_dir.batch_path(self._BATCH_NAME),
                         f'{self._DATASET_PATH}/batch/{self._BATCH_NAME}')

    def test_errors_path(self):
        self.assertEqual(self._dataset_dir.errors_path(self._BATCH_NAME),
                         f'{self._DATASET_PATH}/errors/{self._BATCH_NAME}')

    def test_thumbnails_path(self):
        self.assertEqual(self._dataset_dir.thumbnails_path(self._BATCH_NAME),
                         f'{self._DATASET_PATH}/meta/{self._BATCH_NAME}/thumbnails')

    def test_batch_meta_file(self):
        self.assertEqual(self._dataset_dir.batch_meta_file(self._BATCH_NAME),
                         f'{self._DATASET_PATH}/meta/{self._BATCH_NAME}/_META')

    def test_tmp_path(self):
        self.assertEqual(self._dataset_dir.side_output_path(self._BATCH_NAME),
                         f'{self._DATASET_PATH}/side_output/{self._BATCH_NAME}')

    def test_schema_file(self):
        self.assertEqual(self._dataset_dir.schema_file, f'{self._DATASET_PATH}/schema.json')

    def test_meta_file(self):
        self.assertEqual(self._dataset_dir.meta_file, f'{self._DATASET_PATH}/_META')

    def test_source_batch_path_file(self):
        self.assertEqual(self._dataset_dir.source_batch_path_file(self._BATCH_NAME),
                         f'{self._DATASET_PATH}/batch/{self._BATCH_NAME}/source_batch_path')


if __name__ == '__main__':
    unittest.main()
