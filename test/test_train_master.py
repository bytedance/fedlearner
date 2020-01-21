# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import os
import unittest
from fedlearner_platform.trainer_master.data.data_block import DataBlock
from fedlearner_platform.trainer_master.data.data_block_queue import DataBlockQueue
from fedlearner_platform.trainer_master.data.data_block_set import DataBlockSet
from fedlearner_platform.trainer_master.data.data_source_reader import DataSourceReader
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


class TestDataBlockAlloc(unittest.TestCase):
    def test_trainer_master(self):
        db1 = DataBlock('1', 'data_path1', 'meta_path1')
        db2 = DataBlock('2', 'data_path2', 'meta_path2')
        db_queue = DataBlockQueue()
        db_queue.put(db1)
        db_queue.put(db2)

        self.assertEqual(db_queue.get(), db1)
        self.assertEqual(db_queue.get(), db2)

    def test_data_block_set(self):
        db1 = DataBlock('1', 'data_path1', 'meta_path1')
        db2 = DataBlock('2', 'data_path2', 'meta_path2')
        db_set = DataBlockSet()
        db_set.add(db1)
        db_set.add(db2)

        self.assertIsNone(db_set.get('3'))
        self.assertEqual(db_set.get('1'), db1)
        self.assertIsNone(db_set.get('1'))
        self.assertEqual(db_set.get('2'), db2)
        self.assertIsNone(db_set.get('2'))

    def test_data_block(self):
        db1 = DataBlock('1', 'data_path1', None)
        self.assertRaises(Exception, db1.validate)
        db2 = DataBlock('2', 'data_path2', 'meta_path2')
        self.assertTrue(db2.validate())

    def test_data_block_reader(self):
        ds_reader = DataSourceReader(data_source='data_source',
                                     start_date='2019-01-02',
                                     end_date='2019-10-02')
        self.assertIsNotNone(ds_reader.read_all())


if __name__ == '__main__':
    unittest.main()