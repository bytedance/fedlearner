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

import tarfile
import os
import shutil
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

from envs import Envs
from http import HTTPStatus
from pathlib import Path
from collections import namedtuple

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from testing.common import BaseTestCase

from fedlearner_webconsole.file.apis import UPLOAD_FILE_PATH
from fedlearner_webconsole.utils.file_manager import FileManager

BASE_DIR = Envs.BASE_DIR
FakeFileStatistics = namedtuple('FakeFileStatistics', ['length', 'mtime_nsec', 'is_directory'])

_FAKE_STORAGE_ROOT = str(tempfile.gettempdir())


@patch('fedlearner_webconsole.file.apis.Envs.STORAGE_ROOT', _FAKE_STORAGE_ROOT)
@patch('fedlearner_webconsole.file.apis.FILE_WHITELIST', (_FAKE_STORAGE_ROOT))
class FilesApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self._file_manager = FileManager()
        self._tempdir = os.path.join(_FAKE_STORAGE_ROOT, 'upload')
        os.makedirs(self._tempdir, exist_ok=True)
        subdir = Path(self._tempdir).joinpath('s')
        subdir.mkdir(exist_ok=True)
        Path(self._tempdir).joinpath('f1.txt').write_text('f1', encoding='utf-8')
        Path(self._tempdir).joinpath('f2.txt').write_text('f2f2', encoding='utf-8')
        subdir.joinpath('s3.txt').write_text('s3s3s3', encoding='utf-8')

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self._tempdir)

    def _get_temp_path(self, file_path: str = None) -> str:
        return str(Path(self._tempdir, file_path or '').absolute())

    def test_get_storage_root(self):
        get_response = self.get_helper('/api/v2/files')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(len(self.get_response_data(get_response)), 3)

    def test_get_specified_illegal_directory(self):
        get_response = self.get_helper('/api/v2/files?directory=/var/log')
        self.assertEqual(get_response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_not_exist_directory(self):
        fake_dir = os.path.join(_FAKE_STORAGE_ROOT, 'fake_dir')
        get_response = self.get_helper(f'/api/v2/files?directory={fake_dir}')
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_upload_files(self):
        data = {}
        data['file'] = [(BytesIO(b'abcdef'), os.path.join(BASE_DIR, 'test.jpg')),
                        (BytesIO(b'aaabbb'), os.path.join(BASE_DIR, 'test.txt'))]
        data['id'] = 'jobs/123'
        upload_response = self.client.post('/api/v2/files',
                                           data=data,
                                           content_type='multipart/form-data',
                                           headers=self._get_headers())
        self.assertEqual(upload_response.status_code, HTTPStatus.OK)
        uploaded_files = self.get_response_data(upload_response)
        self.assertEqual(
            {
                'uploaded_files': [{
                    'display_file_name':
                        'test.jpg',
                    'internal_path':
                        os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123', secure_filename('test.jpg')),
                    'internal_directory':
                        os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123'),
                }, {
                    'display_file_name':
                        'test.txt',
                    'internal_path':
                        os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123', secure_filename('test.txt')),
                    'internal_directory':
                        os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123'),
                }],
            }, uploaded_files)

        # Check the saved files.
        self.assertEqual(
            'abcdef',
            self._file_manager.read(
                os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123', secure_filename('test.jpg'))))
        self.assertEqual(
            'aaabbb',
            self._file_manager.read(
                os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123', secure_filename('test.txt'))))

        # Delete the saved files
        self._file_manager.remove(
            os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123', secure_filename('test.jpg')))
        self._file_manager.remove(
            os.path.join(_FAKE_STORAGE_ROOT, UPLOAD_FILE_PATH, 'jobs/123', secure_filename('test.txt')))


@patch('fedlearner_webconsole.file.apis.Envs.STORAGE_ROOT', _FAKE_STORAGE_ROOT)
@patch('fedlearner_webconsole.file.apis.FILE_WHITELIST', (_FAKE_STORAGE_ROOT))
class FileApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self._tempdir = _FAKE_STORAGE_ROOT
        os.makedirs(self._tempdir, exist_ok=True)
        Path(self._tempdir).joinpath('exists.txt').write_text('Hello World', encoding='utf-8')

    def test_get_file_content_api(self):
        get_response = self.get_helper(f'/api/v2/file?path={self._tempdir}/exists.txt')
        self.assertEqual(self.get_response_data(get_response), 'Hello World')

        get_response = self.get_helper('/api/v2/file?path=/system/fd.txt')
        self.assertEqual(get_response.status_code, HTTPStatus.FORBIDDEN)


@patch('fedlearner_webconsole.file.apis.Envs.STORAGE_ROOT', _FAKE_STORAGE_ROOT)
@patch('fedlearner_webconsole.file.apis.FILE_WHITELIST', (_FAKE_STORAGE_ROOT))
class ImageApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.signout_helper()

        self._tempdir = _FAKE_STORAGE_ROOT
        os.makedirs(self._tempdir, exist_ok=True)
        Path(self._tempdir).joinpath('fake_image.jpg').write_bytes(b'This is a image')

    def test_get_image_content_api(self):
        get_response = self.get_helper(f'/api/v2/image?name={self._tempdir}/fake_image.jpg')
        self.assertEqual(get_response.data, b'This is a image')
        self.assertEqual(get_response.mimetype, 'image/jpeg')

        get_response = self.get_helper(f'/api/v2/image?name={self._tempdir}/fd.txt')
        self.assertEqual(get_response.status_code, HTTPStatus.BAD_REQUEST)

        get_response = self.get_helper('/api/v2/image?name=/system/fd.txt')
        self.assertEqual(get_response.status_code, HTTPStatus.FORBIDDEN)


if __name__ == '__main__':
    unittest.main()
