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
import shutil
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from fedlearner_webconsole.utils.file_manager import (
    DefaultFileManager, HdfsFileManager, FileManager)


class DefaultFileManagerTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self._test_dir = tempfile.mkdtemp()
        subdir = Path(self._test_dir).joinpath('subdir')
        subdir.mkdir()
        Path(self._test_dir).joinpath('f1.txt').write_text('xxx')
        Path(self._test_dir).joinpath('f2.txt').write_text('xxx')
        subdir.joinpath('s1.txt').write_text('xxx')
        self.FILE_SIZE = 3

        self._fm = DefaultFileManager()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self._test_dir)

    def _get_temp_path(self, file_path: str = None) -> str:
        return str(Path(self._test_dir, file_path or '').absolute())

    def test_can_handle(self):
        self.assertTrue(self._fm.can_handle('/data/abc'))
        self.assertFalse(self._fm.can_handle('data'))

    def test_ls(self):
        # List file
        self.assertEqual(self._fm.ls(self._get_temp_path('f1.txt')),
                         [{'path': self._get_temp_path('f1.txt'),
                           'size': self.FILE_SIZE}])
        # List folder
        self.assertEqual(
            sorted(self._fm.ls(self._get_temp_path()),
                   key=lambda file: file['path']),
            sorted([
                {'path': self._get_temp_path('f1.txt'),
                 'size': self.FILE_SIZE},
                {'path': self._get_temp_path('f2.txt'),
                 'size': self.FILE_SIZE}
            ], key=lambda file: file['path']))
        # List folder recursively
        self.assertEqual(
            sorted(self._fm.ls(self._get_temp_path(), recursive=True),
                   key=lambda file: file['path']),
            sorted([
                {'path': self._get_temp_path('f1.txt'),
                 'size': self.FILE_SIZE},
                {'path': self._get_temp_path('f2.txt'),
                 'size': self.FILE_SIZE},
                {'path': self._get_temp_path('subdir/s1.txt'),
                 'size': self.FILE_SIZE},
            ], key=lambda file: file['path']))

    def test_move(self):
        # Moves to another folder
        self._fm.move(self._get_temp_path('f1.txt'),
                      self._get_temp_path('subdir/'))
        self.assertEqual(
            sorted(self._fm.ls(self._get_temp_path('subdir')),
                   key=lambda file: file['path']),
            sorted([
                {'path': self._get_temp_path('subdir/s1.txt'),
                 'size': self.FILE_SIZE},
                {'path': self._get_temp_path('subdir/f1.txt'),
                 'size': self.FILE_SIZE},
            ], key=lambda file: file['path']))
        # Renames
        self._fm.move(self._get_temp_path('f2.txt'),
                      self._get_temp_path('f3.txt'))
        self.assertEqual(
            self._fm.ls(self._get_temp_path('f2.txt')), [])
        self.assertEqual(
            self._fm.ls(self._get_temp_path('f3.txt')),
            [{'path': self._get_temp_path('f3.txt'),
              'size': self.FILE_SIZE}])

    def test_remove(self):
        self._fm.remove(self._get_temp_path('f1.txt'))
        self._fm.remove(self._get_temp_path('subdir'))
        self.assertEqual(
            self._fm.ls(self._get_temp_path(), recursive=True),
            [{'path': self._get_temp_path('f2.txt'),
              'size': self.FILE_SIZE}])

    def test_copy(self):
        self._fm.copy(self._get_temp_path('f1.txt'),
                      self._get_temp_path('subdir'))
        self.assertEqual(
            self._fm.ls(self._get_temp_path('f1.txt')),
            [{'path': self._get_temp_path('f1.txt'),
              'size': self.FILE_SIZE}])
        self.assertEqual(
            self._fm.ls(self._get_temp_path('subdir/f1.txt')),
            [{'path': self._get_temp_path('subdir/f1.txt'),
              'size': self.FILE_SIZE}])

    def test_mkdir(self):
        self._fm.mkdir(os.path.join(self._get_temp_path(), 'subdir2'))
        self.assertTrue(os.path.isdir(self._get_temp_path('subdir2')))


class HdfsFileManagerTest(unittest.TestCase):
    def setUp(self):
        self._mock_client = MagicMock()
        self._client_patcher = patch(
            'fedlearner_webconsole.utils.file_manager.AutoConfigClient')
        self._client_patcher.start().return_value = self._mock_client
        self._fm = HdfsFileManager()

    def tearDown(self):
        self._client_patcher.stop()

    def test_can_handle(self):
        self.assertFalse(self._fm.can_handle('/data/abc'))
        self.assertTrue(self._fm.can_handle('hdfs://abc'))

    def test_ls(self):
        mock_ls = MagicMock()
        self._mock_client.ls = mock_ls
        mock_ls.return_value = [
            {'file_type': 'f', 'path': '/data/abc', 'length': 1024},
            {'file_type': 'd', 'path': '/data', 'length': 1024}
        ]
        self.assertEqual(
            self._fm.ls('/data', recursive=True),
            [{'path': '/data/abc', 'size': 1024}]
        )
        mock_ls.assert_called_once_with(['/data'], recurse=True)

    @staticmethod
    def _yield_files(files):
        for file in files:
            yield file

    def test_move(self):
        mock_rename = MagicMock()
        self._mock_client.rename = mock_rename
        mock_rename.return_value = self._yield_files(['/data/123'])
        self.assertTrue(self._fm.move('/data/abc', '/data/123'))
        mock_rename.assert_called_once_with(['/data/abc'], '/data/123')

        mock_rename.return_value = self._yield_files([])
        self.assertFalse(self._fm.move('/data/abc', '/data/123'))

    def test_remove(self):
        mock_delete = MagicMock()
        self._mock_client.delete = mock_delete
        mock_delete.return_value = self._yield_files(['/data/123'])
        self.assertTrue(self._fm.remove('/data/123'))
        mock_delete.assert_called_once_with(['/data/123'])

        mock_delete.return_value = self._yield_files([])
        self.assertFalse(self._fm.remove('/data/123'))

    def test_copy(self):
        # TODO
        pass

    def test_mkdir(self):
        mock_mkdir = MagicMock()
        self._mock_client.mkdir = mock_mkdir
        mock_mkdir.return_value = self._yield_files([{'path': '/data',
                                                      'result': True}])
        self.assertTrue(self._fm.mkdir('/data'))
        mock_mkdir.assert_called_once_with(['/data'], create_parent=True)


class FileManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ[
            'CUSTOMIZED_FILE_MANAGER'] = 'testing.fake_file_manager:FakeFileManager'

    @classmethod
    def tearDownClass(cls):
        del os.environ['CUSTOMIZED_FILE_MANAGER']

    def setUp(self):
        self._fm = FileManager()

    def test_can_handle(self):
        self.assertTrue(self._fm.can_handle('fake://123'))
        # Falls back to default manager
        self.assertTrue(self._fm.can_handle('/data/123'))
        self.assertFalse(self._fm.can_handle('hdfs://123'))

    def test_ls(self):
        self.assertEqual(self._fm.ls('fake://data'), [{
            'path': 'fake://data/f1.txt',
            'size': 0
        }])

    def test_move(self):
        self.assertTrue(self._fm.move('fake://move/123', 'fake://move/234'))
        self.assertFalse(
            self._fm.move('fake://do_not_move/123', 'fake://move/234'))
        # No file manager can handle this
        self.assertRaises(RuntimeError,
                          lambda: self._fm.move('hdfs://123', 'fake://abc'))

    def test_remove(self):
        self.assertTrue(self._fm.remove('fake://remove/123'))
        self.assertFalse(self._fm.remove('fake://do_not_remove/123'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.remove('hdfs://123'))

    def test_copy(self):
        self.assertTrue(self._fm.copy('fake://copy/123', 'fake://copy/234'))
        self.assertFalse(
            self._fm.copy('fake://do_not_copy/123', 'fake://copy/234'))
        # No file manager can handle this
        self.assertRaises(RuntimeError,
                          lambda: self._fm.copy('hdfs://123', 'fake://abc'))

    def test_mkdir(self):
        self.assertTrue(self._fm.mkdir('fake://mkdir/123'))
        self.assertFalse(self._fm.mkdir('fake://do_not_mkdir/123'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.mkdir('hdfs://123'))


if __name__ == '__main__':
    unittest.main()
