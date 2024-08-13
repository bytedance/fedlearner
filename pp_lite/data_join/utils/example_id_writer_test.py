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
from pathlib import Path
from pp_lite.data_join.utils.example_id_writer import ExampleIdWriter


class ExampleIdWriterTest(unittest.TestCase):

    def test_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = ExampleIdWriter(temp_dir, key_column='raw_id')
            writer.write(partition_id=0, ids=['a', 'b'])
            with open(os.path.join(temp_dir, 'partition_0'), encoding='utf-8') as f:
                content = f.read()
                self.assertEqual(content, 'raw_id\na\nb\n')

    def test_write_success_tag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = ExampleIdWriter(temp_dir, key_column='raw_id')
            writer.write_success_tag(partition_id=1)
            self.assertTrue(os.path.exists(os.path.join(temp_dir, '0001._SUCCESS')))

    def test_success_tag_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = ExampleIdWriter(temp_dir, key_column='raw_id')
            self.assertFalse(writer.success_tag_exists(1))
            Path(os.path.join(temp_dir, '0001._SUCCESS')).touch()
            self.assertTrue(writer.success_tag_exists(1))

    def test_combine(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = ExampleIdWriter(temp_dir, key_column='raw_id')
            writer.write(partition_id=0, ids=[1, 2])
            writer.write(partition_id=1, ids=[3, 4])
            writer.write(partition_id=2, ids=[5, 6])
            writer.combine(3)
            with open(os.path.join(temp_dir, 'output.csv'), 'r', encoding='utf-8') as f:
                self.assertEqual(f.read(), 'raw_id\n1\n2\n3\n4\n5\n6\n')


if __name__ == '__main__':
    unittest.main()
