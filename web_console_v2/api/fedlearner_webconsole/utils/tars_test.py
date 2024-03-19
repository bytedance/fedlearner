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
import unittest
import os
import tempfile
import shutil
from pathlib import Path
from fedlearner_webconsole.utils.stream_untars import StreamingUntar
from fedlearner_webconsole.utils.stream_tars import StreamingTar
from fedlearner_webconsole.utils.file_manager import FileManager


class StreamingTarTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self._file_manager = FileManager()
        self._tempdir = os.path.join(tempfile.gettempdir(), 'tar_dir')
        os.makedirs(self._tempdir, exist_ok=True)

    def _get_temp_path(self, file_path: str = None) -> str:
        return str(Path(self._tempdir, file_path or '').absolute())

    def test_untar(self):

        # init a dir with some files
        tar_path = os.path.join(self._tempdir, 'tar')
        self._file_manager.mkdir(tar_path)
        file1_path = os.path.join(tar_path, 'test-tar1.py')
        file2_path = os.path.join(tar_path, 'test-tar2.py')
        file3_path = os.path.join(tar_path, 'new/test-tar3.py')

        self._file_manager.write(file1_path, 'abc')
        self._file_manager.write(file2_path, 'abc')
        self._file_manager.write(file3_path, 'abc')

        # Create a tar file
        tar_file_path = os.path.join(tar_path, 'test-tar.tar.gz')
        StreamingTar(self._file_manager).archive(source_path=[file1_path, file2_path, file3_path],
                                                 target_path=tar_file_path,
                                                 gzip_compress=True)

        # test streaming untar file
        untar_dir = os.path.join(tar_path, 'untar')
        StreamingUntar(self._file_manager).untar(tar_file_path, untar_dir)

        self._file_manager.exists(os.path.join(tar_path, os.path.basename(file1_path)))
        self._file_manager.exists(os.path.join(tar_path, os.path.basename(file2_path)))
        self._file_manager.exists(os.path.join(tar_path, os.path.basename(file3_path)))

    def __del__(self):
        shutil.rmtree(self._tempdir)


if __name__ == '__main__':
    unittest.main()
