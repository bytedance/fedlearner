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
import tempfile
from shutil import rmtree

from pp_lite.data_join.psi_rsa.server.partition_writer import RsaServerPartitionWriter


class RsaServerPartitionWriterTest(unittest.TestCase):

    def setUp(self) -> None:
        self.input_dir: str = tempfile.mkdtemp()
        self.output_dir: str = tempfile.mkdtemp()
        self.parts = []
        for _ in range(5):
            _, path = tempfile.mkstemp(prefix='part-', dir=self.input_dir)
            with open(path, mode='w', encoding='utf-8') as f:
                f.write('raw_id\n1')
        self.writer = RsaServerPartitionWriter(output_dir=self.output_dir, key_column='raw_id')

    def tearDown(self) -> None:
        rmtree(self.input_dir)
        rmtree(self.output_dir)

    def test_write_data_join_result(self):
        self.writer.write_data_join_result(iter([(-1, ['1', '2', '3']), (-1, ['1', '2', '3'])]))
        with open(f'{self.output_dir}/joined/output.csv', mode='r', encoding='utf-8') as f:
            self.assertEqual('raw_id\n1\n2\n3\n1\n2\n3\n', f.read())


if __name__ == '__main__':
    unittest.main()
