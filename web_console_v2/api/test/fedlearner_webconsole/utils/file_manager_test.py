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
        Path(self._test_dir).joinpath('f1.txt').touch()
        Path(self._test_dir).joinpath('f2.txt').touch()
        subdir = Path(self._test_dir).joinpath('subdir')
        subdir.mkdir()
        subdir.joinpath('s1.txt').touch()

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
                             [self._get_temp_path('f1.txt')])
        # List folder
        self.assertEqual(
            self._fm.ls(self._get_temp_path()),
            [
                self._get_temp_path('f1.txt'),
                self._get_temp_path('f2.txt')
            ])
        # List folder recursively
        self.assertEqual(
            self._fm.ls(self._get_temp_path(), recursive=True),
            [
                self._get_temp_path('f1.txt'),
                self._get_temp_path('f2.txt'),
                self._get_temp_path('subdir/s1.txt')
            ])

    def test_move(self):
        # Moves to another folder
        self._fm.move(self._get_temp_path('f1.txt'), self._get_temp_path('subdir/'))
        self.assertEqual(
            self._fm.ls(self._get_temp_path('subdir')),
            [
                self._get_temp_path('subdir/s1.txt'),
                self._get_temp_path('subdir/f1.txt')
            ])
        # Renames
        self._fm.move(self._get_temp_path('f2.txt'), self._get_temp_path('f3.txt'))
        self.assertEqual(
            self._fm.ls(self._get_temp_path('f2.txt')), [])
        self.assertEqual(
            self._fm.ls(self._get_temp_path('f3.txt')),
            [self._get_temp_path('f3.txt')])

    def test_remove(self):
        self._fm.remove(self._get_temp_path('f1.txt'))
        self._fm.remove(self._get_temp_path('subdir'))
        self.assertEqual(
            self._fm.ls(self._get_temp_path(), recursive=True),
            [self._get_temp_path('f2.txt')])


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
            {'file_type': 'f', 'path': '/data/abc'},
            {'file_type': 'd', 'path': '/data'}
        ]
        self.assertEqual(
            self._fm.ls('/data', recursive=True),
            ['/data/abc']
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


class FileManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['CUSTOMIZED_FILE_MANAGER'] = 'testing.fake_file_manager:FakeFileManager'

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
        self.assertEqual(self._fm.ls('fake://data'), ['fake://data/f1.txt'])

    def test_move(self):
        self.assertTrue(self._fm.move('fake://move/123', 'fake://move/234'))
        self.assertFalse(self._fm.move('fake://do_not_move/123', 'fake://move/234'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.move('hdfs://123', 'fake://abc'))

    def test_remove(self):
        self.assertTrue(self._fm.remove('fake://remove/123'))
        self.assertFalse(self._fm.remove('fake://do_not_remove/123'))
        # No file manager can handle this
        self.assertRaises(RuntimeError, lambda: self._fm.remove('hdfs://123'))


if __name__ == '__main__':
    unittest.main()
