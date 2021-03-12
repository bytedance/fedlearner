# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import stat
import time
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock

from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import (Dataset, DatasetType,
                                                  DataBatch)


class DatasetApiTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        STORAGE_ROOT = '/tmp'

    def setUp(self):
        super().setUp()
        self.default_dataset1 = Dataset(
            name='default dataset1',
            dataset_type=DatasetType.STREAMING,
            comment='test comment1',
            path='/data/dataset/123'
        )
        db.session.add(self.default_dataset1)
        db.session.commit()
        time.sleep(1)
        self.default_dataset2 = Dataset(
            name='default dataset2',
            dataset_type=DatasetType.STREAMING,
            comment='test comment2',
            path='123'
        )
        db.session.add(self.default_dataset2)
        db.session.commit()

    def test_get_dataset(self):
        get_response = self.get_helper(
            f'/api/v2/datasets/{self.default_dataset1.id}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset = self.get_response_data(get_response)
        self.assertEqual({
            'id': 1,
            'name': 'default dataset1',
            'dataset_type': 'STREAMING',
            'comment': 'test comment1',
            'path': '/data/dataset/123',
            'created_at': mock.ANY,
            'updated_at': mock.ANY,
            'deleted_at': None,
            'data_batches': []
        }, dataset)

    def test_get_dataset_not_found(self):
        get_response = self.get_helper('/api/v2/datasets/10086')
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_datasets(self):
        get_response = self.get_helper('/api/v2/datasets')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 2)
        self.assertEqual(datasets[0]['name'], 'default dataset2')
        self.assertEqual(datasets[1]['name'], 'default dataset1')

    @patch('fedlearner_webconsole.dataset.apis.datetime')
    def test_post_datasets(self, mock_datetime):
        mock_datetime.now = MagicMock(return_value=datetime(2020, 6, 8, 6, 6, 6))
        name = 'test post dataset'
        dataset_type = DatasetType.STREAMING.value
        comment = 'test comment'
        create_response = self.client.post(
            '/api/v2/datasets',
            data=json.dumps({
                'name': name,
                'dataset_type': dataset_type,
                'comment': comment
            }),
            content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_dataset = self.get_response_data(create_response)

        self.assertEqual({
            'id': 3,
            'name': 'test post dataset',
            'dataset_type': dataset_type,
            'comment': comment,
            'path': '/tmp/dataset/20200608_060606_test-post-dataset',
            'created_at': mock.ANY,
            'updated_at': mock.ANY,
            'deleted_at': None,
            'data_batches': []
        }, created_dataset)

    @patch('fedlearner_webconsole.dataset.apis.scheduler.wakeup')
    def test_post_batches(self, mock_wakeup):
        dataset_id = self.default_dataset1.id
        event_time = int(datetime(2020, 6, 8, 6, 8, 8).timestamp())
        files = ['/data/upload/1.csv', '/data/upload/2.csv']
        move = False
        comment = 'test post comment'
        create_response = self.client.post(
            f'/api/v2/datasets/{dataset_id}/batches',
            data=json.dumps({
                'event_time': event_time,
                'files': files,
                'move': move,
                'comment': comment
            }),
            content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_data_batch = self.get_response_data(create_response)

        self.maxDiff = None
        self.assertEqual({
            'id': 1,
            'dataset_id': 1,
            'comment': comment,
            'event_time': event_time,
            'created_at': mock.ANY,
            'updated_at': mock.ANY,
            'deleted_at': None,
            'file_size': 0,
            'move': False,
            'num_file': 2,
            'num_imported_file': 0,
            'path': '/data/dataset/123/batch/20200608_060808',
            'state': 'NEW',
            'details': {
                'files': [
                    {
                        'destination_path': '/data/dataset/123/batch/20200608_060808/1.csv',
                        'error_message': '',
                        'size': '0',
                        'source_path': '/data/upload/1.csv',
                        'state': 'UNSPECIFIED'
                    },
                    {
                        'destination_path': '/data/dataset/123/batch/20200608_060808/2.csv',
                        'error_message': '',
                        'size': '0',
                        'source_path': '/data/upload/2.csv',
                        'state': 'UNSPECIFIED'
                    }
                ]
            }
        }, created_data_batch)
        mock_wakeup.assert_called_once_with(
            data_batch_ids=[created_data_batch['id']])


class FilesApiTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        STORAGE_ROOT = tempfile.gettempdir()

    def setUp(self):
        super().setUp()
        # Create a temporary directory
        self._tempdir = os.path.join(tempfile.gettempdir(), 'upload')
        os.makedirs(self._tempdir, exist_ok=True)
        subdir = Path(self._tempdir).joinpath('s')
        subdir.mkdir()
        Path(self._tempdir).joinpath('f1.txt').write_text('f1')
        Path(self._tempdir).joinpath('f2.txt').write_text('f2f2')
        subdir.joinpath('s3.txt').write_text('s3s3s3')

        # Mocks os.stat
        self._orig_os_stat = os.stat

        def fake_stat(path, *arg, **kwargs):
            return self._get_file_stat(self._orig_os_stat, path)

        os.stat = fake_stat

    def tearDown(self):
        os.stat = self._orig_os_stat
        # Remove the directory after the test
        shutil.rmtree(self._tempdir)
        super().tearDown()

    def _get_temp_path(self, file_path: str = None) -> str:
        return str(Path(self._tempdir, file_path or '').absolute())

    def _get_file_stat(self, orig_os_stat, path):
        if path == self._get_temp_path('f1.txt') or \
            path == self._get_temp_path('f2.txt') or \
            path == self._get_temp_path('s/s3.txt'):
            faked = list(orig_os_stat(path))
            faked[stat.ST_MTIME] = 1613982390
            return os.stat_result(faked)
        else:
            return orig_os_stat(path)

    def test_get_default_storage_root(self):
        get_response = self.get_helper(
            '/api/v2/files')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        files = self.get_response_data(get_response)
        self.assertEqual(sorted(files, key=lambda f: f['size']), [
            {'path': self._get_temp_path('f1.txt'),
             'size': 2,
             'mtime': 1613982390},
            {'path': self._get_temp_path('f2.txt'),
             'size': 4,
             'mtime': 1613982390},
            {'path': self._get_temp_path('s/s3.txt'),
             'size': 6,
             'mtime': 1613982390},
        ])

    def test_get_specified_directory(self):
        dir = self._get_temp_path('s')
        get_response = self.get_helper(
            f'/api/v2/files?directory={dir}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        files = self.get_response_data(get_response)
        self.assertEqual(files, [
            {'path': self._get_temp_path('s/s3.txt'),
             'size': 6,
             'mtime': 1613982390},
        ])


if __name__ == '__main__':
    unittest.main()
