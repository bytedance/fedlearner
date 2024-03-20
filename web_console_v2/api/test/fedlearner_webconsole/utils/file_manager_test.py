# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

from collections import namedtuple
from pathlib import Path
from tensorflow.io import gfile

from fedlearner_webconsole.utils.file_manager import GFileFileManager, FileManager, File

FakeFileStatistics = namedtuple('FakeFileStatistics', ['length', 'mtime_nsec'])


class GFileFileManagerTest(unittest.TestCase):

    _F1_SIZE = 3
    _F2_SIZE = 4
    _S1_SIZE = 55
    _F1_MTIME = 1613982390
    _F2_MTIME = 1613982391
    _S1_MTIME = 1613982392

    def _get_file_stat(self, orig_os_stat, path):
        gfile_stat = FakeFileStatistics(2, 1613982390 * 1e9)
        if path == self._get_temp_path('f1.txt') or \
                path == self._get_temp_path('subdir/f1.txt'):
            gfile_stat = FakeFileStatistics(self._F1_SIZE,
                                            self._F1_MTIME * 1e9)
            return gfile_stat
        elif path == self._get_temp_path('f2.txt') or \
                path == self._get_temp_path('f3.txt'):
            gfile_stat = FakeFileStatistics(self._F2_SIZE,
                                            self._F2_MTIME * 1e9)
            return gfile_stat
        elif path == self._get_temp_path('subdir/s1.txt'):
            gfile_stat = FakeFileStatistics(self._S1_SIZE,
                                            self._S1_MTIME * 1e9)
            return gfile_stat
        else:
            return orig_os_stat(path)

    def setUp(self):
        # Create a temporary directory
        self._test_dir = tempfile.mkdtemp()
        subdir = Path(self._test_dir).joinpath('subdir')
        subdir.mkdir(exist_ok=True)
        Path(self._test_dir).joinpath('f1.txt').write_text('xxx')
        Path(self._test_dir).joinpath('f2.txt').write_text('xxx')
        subdir.joinpath('s1.txt').write_text('xxx')

        # Mocks os.stat
        self._orig_os_stat = os.stat

        def fake_stat(path, *arg, **kwargs):
            return self._get_file_stat(self._orig_os_stat, path)

        gfile.stat = fake_stat

        self._fm = GFileFileManager()

    def tearDown(self):
        os.stat = self._orig_os_stat
        # Remove the directory after the test
        shutil.rmtree(self._test_dir)

    def _get_temp_path(self, file_path: str = None) -> str:
        return str(Path(self._test_dir, file_path or '').absolute())

    def test_can_handle(self):
        self.assertTrue(self._fm.can_handle('/data/abc'))
        self.assertFalse(self._fm.can_handle('data'))

    def test_ls(self):
        # List file
        self.assertEqual(self._fm.ls(self._get_temp_path('f1.txt')), [
            File(path=self._get_temp_path('f1.txt'),
                 size=self._F1_SIZE,
                 mtime=self._F1_MTIME)
        ])
        # List folder
        self.assertEqual(
            sorted(self._fm.ls(self._get_temp_path()),
                   key=lambda file: file.path),
            sorted([
                File(path=self._get_temp_path('f1.txt'),
                     size=self._F1_SIZE,
                     mtime=self._F1_MTIME),
                File(path=self._get_temp_path('f2.txt'),
                     size=self._F2_SIZE,
                     mtime=self._F2_MTIME)
            ],
                   key=lambda file: file.path))
        # List folder recursively
        self.assertEqual(
            sorted(self._fm.ls(self._get_temp_path(), recursive=True),
                   key=lambda file: file.path),
            sorted([
                File(path=self._get_temp_path('f1.txt'),
                     size=self._F1_SIZE,
                     mtime=self._F1_MTIME),
                File(path=self._get_temp_path('f2.txt'),
                     size=self._F2_SIZE,
                     mtime=self._F2_MTIME),
                File(path=self._get_temp_path('subdir/s1.txt'),
                     size=self._S1_SIZE,
                     mtime=self._S1_MTIME),
            ],
                   key=lambda file: file.path))

    def test_move(self):
        # Moves to another folder
        self._fm.move(self._get_temp_path('f1.txt'),
                      self._get_temp_path('subdir/'))
        self.assertEqual(
            sorted(self._fm.ls(self._get_temp_path('subdir')),
                   key=lambda file: file.path),
            sorted([
                File(path=self._get_temp_path('subdir/s1.txt'),
                     size=self._S1_SIZE,
                     mtime=self._S1_MTIME),
                File(path=self._get_temp_path('subdir/f1.txt'),
                     size=self._F1_SIZE,
                     mtime=self._F1_MTIME),
            ],
                   key=lambda file: file.path))
        # Renames
        self._fm.move(self._get_temp_path('f2.txt'),
                      self._get_temp_path('f3.txt'))
        with self.assertRaises(ValueError):
            self._fm.ls(self._get_temp_path('f2.txt'))
        self.assertEqual(self._fm.ls(self._get_temp_path('f3.txt')), [
            File(path=self._get_temp_path('f3.txt'),
                 size=self._F2_SIZE,
                 mtime=self._F2_MTIME)
        ])

    def test_remove(self):
        self._fm.remove(self._get_temp_path('f1.txt'))
        self._fm.remove(self._get_temp_path('subdir'))
        self.assertEqual(self._fm.ls(self._get_temp_path(), recursive=True), [
            File(path=self._get_temp_path('f2.txt'),
                 size=self._F2_SIZE,
                 mtime=self._F2_MTIME)
        ])

    def test_copy(self):
        self._fm.copy(self._get_temp_path('f1.txt'),
                      self._get_temp_path('subdir'))
        self.assertEqual(self._fm.ls(self._get_temp_path('f1.txt')), [
            File(path=self._get_temp_path('f1.txt'),
                 size=self._F1_SIZE,
                 mtime=self._F1_MTIME)
        ])
        self.assertEqual(self._fm.ls(self._get_temp_path('subdir/f1.txt')), [
            File(path=self._get_temp_path('subdir/f1.txt'),
                 size=self._F1_SIZE,
                 mtime=self._F1_MTIME)
        ])

    def test_mkdir(self):
        self._fm.mkdir(os.path.join(self._get_temp_path(), 'subdir2'))
        self.assertTrue(os.path.isdir(self._get_temp_path('subdir2')))

    def test_read(self):
        content = self._fm.read(self._get_temp_path('f1.txt'))
        self.assertEqual('xxx', content)


class FileManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_fm = 'testing.fake_file_manager:FakeFileManager'
        os.environ['CUSTOMIZED_FILE_MANAGER'] = fake_fm

    @classmethod
    def tearDownClass(cls):
        del os.environ['CUSTOMIZED_FILE_MANAGER']

    def setUp(self):
        self._fm = FileManager()

    def test_can_handle(self):
        self.assertTrue(self._fm.can_handle('fake://123'))
        # Falls back to default manager
        self.assertTrue(self._fm.can_handle('/data/123'))
        self.assertFalse(self._fm.can_handle('unsupported:///123'))

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
        self.assertRaises(RuntimeError,
                          lambda: self._fm.remove('unsupported://123'))

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
        self.assertRaises(RuntimeError,
                          lambda: self._fm.mkdir('unsupported:///123'))


if __name__ == '__main__':
    unittest.main()
