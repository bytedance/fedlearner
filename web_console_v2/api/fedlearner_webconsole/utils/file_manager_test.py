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
import shutil
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch
from tensorflow.python.framework.errors_impl import NotFoundError, InvalidArgumentError

from fedlearner_webconsole.utils.file_manager import GFileFileManager, FileManager, File


class GFileFileManagerTest(unittest.TestCase):
    _F1_SIZE = 3
    _F2_SIZE = 3
    _S1_SIZE = 3
    _SUB_SIZE = 4096

    def setUp(self):
        # Create a temporary directory
        self._test_dir = tempfile.mkdtemp()
        subdir = Path(self._test_dir).joinpath('subdir')
        subdir.mkdir(exist_ok=True)
        Path(self._test_dir).joinpath('f1.txt').write_text('xxx', encoding='utf-8')
        Path(self._test_dir).joinpath('f2.txt').write_text('xxx', encoding='utf-8')
        subdir.joinpath('s1.txt').write_text('xxx', encoding='utf-8')

        self._fm = GFileFileManager()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self._test_dir)

    def _assert_file(self, file: File, path: str, size: int, is_directory: bool):
        self.assertEqual(file.path, path)
        self.assertEqual(file.size, size)
        self.assertEqual(file.is_directory, is_directory)

    def _get_temp_path(self, file_path: str = None) -> str:
        return str(Path(self._test_dir, file_path or '').absolute())

    def test_can_handle(self):
        self.assertTrue(self._fm.can_handle('/data/abc'))
        self.assertFalse(self._fm.can_handle('data'))

    def test_info(self):
        info = self._fm.info(self._get_temp_path('f1.txt'))
        self.assertEqual(info['name'], self._get_temp_path('f1.txt'))
        self.assertEqual(info['type'], 'file')
        with patch('fsspec.implementations.local.LocalFileSystem.info') as mock_info:
            mock_info.return_value = {'last_modified': 1}
            info = self._fm.info(self._get_temp_path('f1.txt'))
            self.assertEqual(info, {'last_modified': 1, 'last_modified_time': 1})

    def test_ls(self):
        # List file
        files = self._fm.ls(self._get_temp_path('f1.txt'))
        self.assertEqual(len(files), 1)
        self._assert_file(files[0], self._get_temp_path('f1.txt'), self._F1_SIZE, False)
        with patch('fsspec.implementations.local.LocalFileSystem.info') as mock_info:
            mock_info.return_value = {
                'name': self._get_temp_path('f1.txt'),
                'size': 3,
                'type': 'file',
                'last_modified': 1
            }
            files = self._fm.ls(self._get_temp_path('f1.txt'))
            self._assert_file(files[0], self._get_temp_path('f1.txt'), self._F1_SIZE, False)
            self.assertEqual(files[0].mtime, 1)
        # List folder
        files = sorted(self._fm.ls(self._get_temp_path()), key=lambda file: file.path)
        self.assertEqual(len(files), 2)
        self._assert_file(files[0], self._get_temp_path('f1.txt'), self._F1_SIZE, False)
        self._assert_file(files[1], self._get_temp_path('f2.txt'), self._F2_SIZE, False)
        # List directories
        files = sorted(self._fm.ls(self._get_temp_path(), include_directory=True), key=lambda file: file.path)
        self.assertEqual(len(files), 3)
        self._assert_file(files[0], self._get_temp_path('f1.txt'), self._F1_SIZE, False)
        self._assert_file(files[1], self._get_temp_path('f2.txt'), self._F2_SIZE, False)
        self._assert_file(files[2], self._get_temp_path('subdir'), self._SUB_SIZE, True)

    def test_ls_when_path_has_protocol(self):
        path1 = 'file://' + self._get_temp_path('f1.txt')
        files = self._fm.ls(path1)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].path, path1)
        path2 = 'file://' + self._get_temp_path()
        files = sorted(self._fm.ls(path2), key=lambda file: file.path)
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].path, 'file://' + self._get_temp_path('f1.txt'))
        self.assertEqual(files[1].path, 'file://' + self._get_temp_path('f2.txt'))
        files = sorted(self._fm.ls(path2, include_directory=True), key=lambda file: file.path)
        self.assertEqual(len(files), 3)
        self.assertEqual(files[0].path, 'file://' + self._get_temp_path('f1.txt'))
        self.assertEqual(files[1].path, 'file://' + self._get_temp_path('f2.txt'))
        self.assertEqual(files[2].path, 'file://' + self._get_temp_path('subdir'))

    def test_move(self):
        # Moves to another folder
        self._fm.move(self._get_temp_path('f1.txt'), self._get_temp_path('subdir/'))
        files = sorted(self._fm.ls(self._get_temp_path('subdir')), key=lambda file: file.path)
        self.assertEqual(len(files), 2)
        self._assert_file(files[0], self._get_temp_path('subdir/f1.txt'), self._F1_SIZE, False)
        self._assert_file(files[1], self._get_temp_path('subdir/s1.txt'), self._S1_SIZE, False)
        # Renames
        self._fm.move(self._get_temp_path('f2.txt'), self._get_temp_path('f3.txt'))
        with self.assertRaises(ValueError):
            self._fm.ls(self._get_temp_path('f2.txt'))
        files = self._fm.ls(self._get_temp_path('f3.txt'))
        self.assertEqual(len(files), 1)
        self._assert_file(files[0], self._get_temp_path('f3.txt'), self._F2_SIZE, False)

    def test_remove(self):
        self._fm.remove(self._get_temp_path('f1.txt'))
        self._fm.remove(self._get_temp_path('subdir'))
        files = self._fm.ls(self._get_temp_path(), include_directory=True)
        self.assertEqual(len(files), 1)
        self._assert_file(files[0], self._get_temp_path('f2.txt'), self._F2_SIZE, False)

    def test_copy(self):
        self._fm.copy(self._get_temp_path('f1.txt'), self._get_temp_path('subdir'))
        files = self._fm.ls(self._get_temp_path('f1.txt'))
        self.assertEqual(len(files), 1)
        self._assert_file(files[0], self._get_temp_path('f1.txt'), self._F1_SIZE, False)
        files = self._fm.ls(self._get_temp_path('subdir/f1.txt'))
        self.assertEqual(len(files), 1)
        self._assert_file(files[0], self._get_temp_path('subdir/f1.txt'), self._F1_SIZE, False)

    def test_mkdir(self):
        self._fm.mkdir(os.path.join(self._get_temp_path(), 'subdir2'))
        self.assertTrue(os.path.isdir(self._get_temp_path('subdir2')))

    def test_read(self):
        content = self._fm.read(self._get_temp_path('f1.txt'))
        self.assertEqual('xxx', content)

    def test_write(self):
        self.assertRaises(ValueError, lambda: self._fm.write(self._get_temp_path(), 'aaa'))

        first_write_content = 'aaaa'
        second_write_content = 'bbbb'
        self._fm.write(self._get_temp_path('abc/write.txt'), first_write_content)
        self.assertEqual(first_write_content, self._fm.read(self._get_temp_path('abc/write.txt')))
        self._fm.write(self._get_temp_path('abc/write.txt'), second_write_content)
        self.assertEqual(second_write_content, self._fm.read(self._get_temp_path('abc/write.txt')))

    def test_listdir(self):
        names = self._fm.listdir(self._get_temp_path())
        self.assertCountEqual(names, ['f1.txt', 'f2.txt', 'subdir'])
        with self.assertRaises(ValueError):
            self._fm.listdir(self._get_temp_path('not_exist_path'))

    def test_rename(self):
        first_write_content = 'aaaa'
        self._fm.write(self._get_temp_path('abc/write.txt'), first_write_content)
        self.assertRaises(
            NotFoundError,
            lambda: self._fm.rename(self._get_temp_path('abc/write.txt'), self._get_temp_path('abcd/write.txt')))
        self._fm.rename(self._get_temp_path('abc/write.txt'), self._get_temp_path('read.txt'))
        self.assertEqual(first_write_content, self._fm.read(self._get_temp_path('read.txt')))
        self.assertRaises(InvalidArgumentError,
                          lambda: self._fm.rename(self._get_temp_path('abc'), self._get_temp_path('abc/abc')))
        self.assertRaises(NotFoundError,
                          lambda: self._fm.rename(self._get_temp_path('abc'), self._get_temp_path('abcd/abc')))
        self._fm.mkdir(self._get_temp_path('abcd'))
        self._fm.rename(self._get_temp_path('abc'), self._get_temp_path('abcd/abcd'))
        self.assertTrue(os.path.isdir(self._get_temp_path('abcd/abcd')))


class FileManagerTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        fake_fm = 'testing.fake_file_manager:FakeFileManager'
        self._patcher = patch('fedlearner_webconsole.utils.file_manager.Envs.CUSTOMIZED_FILE_MANAGER', fake_fm)
        self._patcher.start()
        self._fm = FileManager()

    def tearDown(self):
        self._patcher.stop()

    def test_can_handle(self):
        self.assertTrue(self._fm.can_handle('fake://123'))
        # Falls back to default manager
        self.assertTrue(self._fm.can_handle('/data/123'))
        self.assertFalse(self._fm.can_handle('unsupported:///123'))

    def test_ls(self):
        self.assertEqual(self._fm.ls('fake://data'), [{'path': 'fake://data/f1.txt', 'size': 0}])

    def test_move(self):
        self.assertTrue(self._fm.move('fake://move/123', 'fake://move/234'))
        self.assertFalse(self._fm.move('fake://do_not_move/123', 'fake://move/234'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.move('hdfs://123', 'fake://abc'))

    def test_remove(self):
        self.assertTrue(self._fm.remove('fake://remove/123'))
        self.assertFalse(self._fm.remove('fake://do_not_remove/123'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.remove('unsupported://123'))

    def test_copy(self):
        self.assertTrue(self._fm.copy('fake://copy/123', 'fake://copy/234'))
        self.assertFalse(self._fm.copy('fake://do_not_copy/123', 'fake://copy/234'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.copy('hdfs://123', 'fake://abc'))

    def test_mkdir(self):
        self.assertTrue(self._fm.mkdir('fake://mkdir/123'))
        self.assertFalse(self._fm.mkdir('fake://do_not_mkdir/123'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.mkdir('unsupported:///123'))


if __name__ == '__main__':
    unittest.main()
