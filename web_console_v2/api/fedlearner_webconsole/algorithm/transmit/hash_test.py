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

import tempfile
import unittest

from pathlib import Path

from fedlearner_webconsole.algorithm.transmit.hash import get_file_md5
from fedlearner_webconsole.utils.file_manager import FileManager


class HashTest(unittest.TestCase):

    def test_get_file_md5(self):
        with tempfile.NamedTemporaryFile() as f:
            Path(f.name).write_text('hello world', encoding='utf-8')
            self.assertEqual(get_file_md5(FileManager(), f.name), '5eb63bbbe01eeed093cb22bb8f5acdc3')

    def test_get_file_md5_empty_file(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(get_file_md5(FileManager(), f.name), 'd41d8cd98f00b204e9800998ecf8427e')


if __name__ == '__main__':
    unittest.main()
