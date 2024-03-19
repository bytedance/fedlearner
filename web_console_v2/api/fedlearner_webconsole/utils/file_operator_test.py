# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import tempfile
import unittest
from pathlib import Path

from envs import Envs

from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.utils.file_manager import FILE_PREFIX


class FileOperatorTest(unittest.TestCase):

    def test_copy(self):
        fo = FileOperator()
        source = os.path.join(Envs.BASE_DIR, 'testing/test_data/sparkapp.tar')
        with tempfile.TemporaryDirectory() as tmp_dir:
            fo.copy_to(source, tmp_dir)
            dest = os.path.join(tmp_dir, os.path.basename(source))
            self.assertTrue(os.path.exists(dest), 'sparkapp.tar not found')

        with tempfile.TemporaryDirectory() as tmp_dir:
            fo.copy_to(source, tmp_dir, extract=True)
            self.assertTrue(len(os.listdir(tmp_dir)) > 0, 'sparkapp/ not found')

    def test_getsize(self):
        temp_dir = tempfile.mkdtemp()
        # 1 byte
        Path(temp_dir).joinpath('f1.txt').write_text('1', encoding='utf-8')
        # 2 bytes
        Path(temp_dir).joinpath('f2.txt').write_text('22', encoding='utf-8')
        subdir = Path(temp_dir).joinpath('subdir')
        subdir.mkdir(exist_ok=True)
        # 3 bytes
        Path(subdir).joinpath('f3.txt').write_text('333', encoding='utf-8')
        fo = FileOperator()
        # Folder
        self.assertEqual(fo.getsize(str(Path(temp_dir).resolve())), 6)
        # File
        self.assertEqual(fo.getsize(str(Path(temp_dir).joinpath('f2.txt').resolve())), 2)
        # Invalid path
        self.assertEqual(fo.getsize('/invalidfolder/notexist'), 0)

    def test_archive_to(self):
        fo = FileOperator()
        source = os.path.join(Envs.BASE_DIR, 'testing/test_data/algorithm/e2e_test')
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = os.path.join(tmp_dir, os.path.basename(source))
            dest = dest + '.tar'
            fo.archive_to(source, dest)
            self.assertTrue(os.path.exists(dest), 'dest tar file not found')

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = os.path.join(tmp_dir, os.path.basename(source))
            dest = dest + '.tar'
            fo.archive_to(FILE_PREFIX + source, FILE_PREFIX + dest)
            self.assertTrue(os.path.exists(dest), 'dest tar file not found')

    def test_extract_to(self):
        fo = FileOperator()
        source = os.path.join(Envs.BASE_DIR, 'testing/test_data/sparkapp.tar')
        with tempfile.TemporaryDirectory() as tmp_dir:
            fo.extract_to(source, tmp_dir)
            dest = os.path.join(tmp_dir, 'class.csv')
            self.assertTrue(os.path.exists(dest), 'dest tar file not found')

        with tempfile.TemporaryDirectory() as tmp_dir:
            fo.extract_to(FILE_PREFIX + source, FILE_PREFIX + tmp_dir)
            dest = os.path.join(tmp_dir, 'class.csv')
            self.assertTrue(os.path.exists(dest), 'dest tar file not found')


if __name__ == '__main__':
    unittest.main()
