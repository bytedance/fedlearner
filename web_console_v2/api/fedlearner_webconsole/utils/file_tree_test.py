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
from pathlib import Path
from unittest.mock import patch
from testing.common import BaseTestCase
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.file_tree import FileTreeBuilder
from fedlearner_webconsole.utils.file_manager import File


class FileTreeTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        path = tempfile.mkdtemp()
        path = Path(path, 'e2e_test').resolve()
        self._base_path = str(path)
        path.mkdir()
        path.joinpath('follower').mkdir()
        path.joinpath('leader').mkdir()
        file_path = path.joinpath('leader').joinpath('main.py')
        file_path.touch()
        file_path.write_text('import tensorflow')  # pylint: disable=unspecified-encoding

    def test_build(self):
        file_trees = FileTreeBuilder(self._base_path, relpath=True).build()
        data = [to_dict(file_tree) for file_tree in file_trees]
        data = sorted(data, key=lambda d: d['filename'])
        self.assertPartiallyEqual(data[0], {
            'filename': 'follower',
            'path': 'follower',
            'is_directory': True,
            'files': []
        },
                                  ignore_fields=['mtime', 'size'])
        self.assertPartiallyEqual(data[1], {
            'filename': 'leader',
            'path': 'leader',
            'is_directory': True
        },
                                  ignore_fields=['size', 'mtime', 'files'])
        self.assertPartiallyEqual(data[1]['files'][0], {
            'filename': 'main.py',
            'path': 'leader/main.py',
            'is_directory': False
        },
                                  ignore_fields=['size', 'mtime', 'files'])

    def test_build_with_root(self):
        root = FileTreeBuilder(self._base_path, relpath=True).build_with_root()
        data = to_dict(root)
        self.assertPartiallyEqual(data, {
            'filename': 'e2e_test',
            'path': '',
            'is_directory': True
        },
                                  ignore_fields=['size', 'mtime', 'files'])
        files = data['files']
        files = sorted(files, key=lambda f: f['filename'])
        self.assertPartiallyEqual(files[0], {
            'filename': 'follower',
            'path': 'follower',
            'is_directory': True,
            'files': []
        },
                                  ignore_fields=['mtime', 'size'])
        self.assertPartiallyEqual(files[1], {
            'filename': 'leader',
            'path': 'leader',
            'is_directory': True
        },
                                  ignore_fields=['size', 'mtime', 'files'])
        self.assertPartiallyEqual(files[1]['files'][0], {
            'filename': 'main.py',
            'path': 'leader/main.py',
            'is_directory': False
        },
                                  ignore_fields=['size', 'mtime', 'files'])

    @patch('fedlearner_webconsole.utils.file_manager.GFileFileManager.info')
    @patch('fedlearner_webconsole.utils.file_manager.GFileFileManager.ls')
    def test_build_when_ls_corner_case(self, mock_ls, mock_info):
        mock_ls.side_effect = [
            [
                File(path='hdfs://browser-hdfs/business/content-cloud/fedlearner/20221113/leader',
                     size=1,
                     is_directory=True,
                     mtime=1),
                File(path='hdfs://browser-hdfs/business/content-cloud/fedlearner/20221113/leader.py',
                     size=1,
                     is_directory=False,
                     mtime=1),
                File(path='hdfs://browser-hdfs/business/content-cloud/fedlearner/20221113/follower.py',
                     size=1,
                     is_directory=False,
                     mtime=1)
            ],
            [
                File(path='hdfs://browser-hdfs/business/content-cloud/fedlearner/20221113/leader/main.py',
                     size=1,
                     is_directory=False,
                     mtime=1)
            ]
        ]
        mock_info.side_effect = [{
            'name': '/business/content-cloud/fedlearner/20221113'
        }, {
            'name': '/business/content-cloud/fedlearner/20221113'
        }]
        path = 'hdfs://browser-hdfs/business/content-cloud/fedlearner/20221113'
        file_trees = FileTreeBuilder(path=path, relpath=True).build()
        data = [to_dict(file_tree) for file_tree in file_trees]
        data = sorted(data, key=lambda d: d['filename'])
        self.assertPartiallyEqual(data[0], {
            'filename': 'follower.py',
            'path': 'follower.py',
            'is_directory': False,
            'files': []
        },
                                  ignore_fields=['mtime', 'size'])
        self.assertPartiallyEqual(data[1], {
            'filename':
                'leader',
            'path':
                'leader',
            'is_directory':
                True,
            'files': [{
                'filename': 'main.py',
                'path': 'leader/main.py',
                'size': 1,
                'mtime': 1,
                'is_directory': False,
                'files': []
            }]
        },
                                  ignore_fields=['mtime', 'size'])
        self.assertPartiallyEqual(data[2], {
            'filename': 'leader.py',
            'path': 'leader.py',
            'is_directory': False,
            'files': []
        },
                                  ignore_fields=['mtime', 'size'])


if __name__ == '__main__':
    unittest.main()
