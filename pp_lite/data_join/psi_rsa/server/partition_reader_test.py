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
import tempfile
from shutil import rmtree

from pp_lite.data_join.psi_rsa.server.partition_reader import RsaServerPartitionReader


class RsaServerPartitionReaderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.input_dir: str = tempfile.mkdtemp()
        cls.parts = []
        for _ in range(5):
            _, path = tempfile.mkstemp(prefix='part-', dir=cls.input_dir)
            with open(path, mode='w', encoding='utf-8') as f:
                f.write('signed_id\n1')
        cls.helper = RsaServerPartitionReader(input_dir=cls.input_dir, signed_column='signed_id', batch_size=32)

    @classmethod
    def tearDownClass(cls) -> None:
        rmtree(cls.input_dir)

    def test_get_files_under(self):
        files = self.helper._get_files_under(self.input_dir)
        self.assertEqual(5, len(files))

    def test_get_partition_num(self):
        num = self.helper.get_partition_num()
        self.assertEqual(5, num)

    def test_get_files_by_partition_id(self):
        ids = [id.partition('part-')[-1] for id in self.parts]
        self.assertEqual(5, len(self.helper._get_files_by_partition_id(ids)))
        self.assertEqual(5, len(self.helper._get_files_by_partition_id(None)))
        self.assertEqual(3, len(self.helper._get_files_by_partition_id(ids)[:3]))
        self.assertEqual(5, len(self.helper._get_files_by_partition_id([])))


if __name__ == '__main__':
    unittest.main()
