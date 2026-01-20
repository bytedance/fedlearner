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
import unittest
import tempfile
from pp_lite.proto.common_pb2 import FileType
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader, PartitionInfo
from pp_lite.testing.make_data import _make_fake_data


class PartitionInfoTest(unittest.TestCase):

    def test_num_partitions(self):
        with tempfile.TemporaryDirectory() as input_dir:
            _make_fake_data(input_dir, num_partitions=10, line_num=10)
            partition_reader = PartitionInfo(input_dir)
            self.assertEqual(partition_reader.num_partitions, 10)

    def test_get_file(self):
        with tempfile.TemporaryDirectory() as input_dir:
            _make_fake_data(input_dir, num_partitions=10, line_num=10, partitioned=True, spark=False)
            partition_reader = PartitionInfo(input_dir)
            files = partition_reader.get_files(partition_id=1)
            self.assertEqual(files, [os.path.join(input_dir, 'part-1')])

    def test_get_file_spark(self):
        with tempfile.TemporaryDirectory() as input_dir:
            _make_fake_data(input_dir, num_partitions=10, line_num=10, partitioned=True, spark=True)
            partition_reader = PartitionInfo(input_dir)
            files = partition_reader.get_files(partition_id=1)
            files = [files[0].split('-')[0] + '-' + files[0].split('-')[1]]
            self.assertEqual(files, [os.path.join(input_dir, 'part-1')])

    def test_get_all_files(self):
        with tempfile.TemporaryDirectory() as input_dir:
            _make_fake_data(input_dir, num_partitions=10, line_num=10, partitioned=False)
            partition_reader = PartitionInfo(input_dir)
            files = partition_reader.get_all_files()
            self.assertEqual(sorted(files), [f'{input_dir}/abcd-{str(i)}' for i in range(10)])


class ExampleIdReaderTest(unittest.TestCase):

    def test_read(self):
        with tempfile.TemporaryDirectory() as input_dir:
            _make_fake_data(input_dir, num_partitions=10, line_num=10)
            reader = ExampleIdReader(input_dir, FileType.CSV, key_column='part_id')
            values = reader.read(partition_id=1)
            self.assertEqual(values, ['1'] * 10)

    def test_read_all(self):
        with tempfile.TemporaryDirectory() as input_dir:
            _make_fake_data(input_dir, num_partitions=10, line_num=10, partitioned=False)
            reader = ExampleIdReader(input_dir, FileType.CSV, key_column='part_id')
            values = reader.read_all()
            self.assertEqual(len(values), 100)


if __name__ == '__main__':
    unittest.main()
