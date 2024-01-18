# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import json
import time
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock

from collections import namedtuple
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db_handler as db
from fedlearner_webconsole.dataset.models import (Dataset, DatasetType)
from tensorflow.io import gfile

FakeFileStatistics = namedtuple('FakeFileStatistics', ['length', 'mtime_nsec'])


class DatasetApiTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        STORAGE_ROOT = tempfile.gettempdir()

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            self.default_dataset1 = Dataset(
                name='default dataset1',
                dataset_type=DatasetType.STREAMING,
                comment='test comment1',
                path='/data/dataset/123',
                project_id=1,
            )
            session.add(self.default_dataset1)
            session.commit()
        time.sleep(1)
        with db.session_scope() as session:
            self.default_dataset2 = Dataset(
                name='default dataset2',
                dataset_type=DatasetType.STREAMING,
                comment='test comment2',
                path=os.path.join(tempfile.gettempdir(), 'dataset/123'),
                project_id=2,
            )
            session.add(self.default_dataset2)
            session.commit()

    def test_get_dataset(self):
        get_response = self.get_helper(
            f'/api/v2/datasets/{self.default_dataset1.id}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        dataset = self.get_response_data(get_response)
        self.assertEqual(
            {
                'id': 1,
                'name': 'default dataset1',
                'dataset_type': 'STREAMING',
                'comment': 'test comment1',
                'path': '/data/dataset/123',
                'created_at': mock.ANY,
                'updated_at': mock.ANY,
                'deleted_at': None,
                'data_batches': [],
                'project_id': 1,
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

    def test_get_datasets_with_project_id(self):
        get_response = self.get_helper('/api/v2/datasets?project=1')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        datasets = self.get_response_data(get_response)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]['name'], 'default dataset1')

    def test_preview_dataset_and_feature_metrics(self):
        # write data
        gfile.makedirs(self.default_dataset2.path)
        meta_path = os.path.join(self.default_dataset2.path, '_META')
        meta_data = {
            'dtypes': {
                'f01': 'bigint'
            },
            'samples': [
                [1],
                [0],
            ],
        }
        with gfile.GFile(meta_path, 'w') as f:
            f.write(json.dumps(meta_data))

        features_path = os.path.join(self.default_dataset2.path, '_FEATURES')
        features_data = {
            'f01': {
                'count': '2',
                'mean': '0.0015716767309123998',
                'stddev': '0.03961485047808605',
                'min': '0',
                'max': '1',
                'missing_count': '0'
            }
        }
        with gfile.GFile(features_path, 'w') as f:
            f.write(json.dumps(features_data))

        hist_path = os.path.join(self.default_dataset2.path, '_HIST')
        hist_data = {
            "f01": {
                "x": [
                    0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5,
                    0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1
                ],
                "y": [12070, 0, 0, 0, 0, 0, 0, 0, 0, 19]
            }
        }
        with gfile.GFile(hist_path, 'w') as f:
            f.write(json.dumps(hist_data))

        response = self.client.get('/api/v2/datasets/2/preview')
        self.assertEqual(response.status_code, 200)
        preview_data = self.get_response_data(response)
        meta_data['metrics'] = features_data
        self.assertEqual(preview_data, meta_data, 'should has preview data')

        feat_name = 'f01'
        feature_response = self.client.get(
            f'/api/v2/datasets/2/feature_metrics?name={feat_name}')
        self.assertEqual(response.status_code, 200)
        feature_data = self.get_response_data(feature_response)
        self.assertEqual(
            feature_data, {
                'name': feat_name,
                'metrics': features_data.get(feat_name, {}),
                'hist': hist_data.get(feat_name, {})
            }, 'should has feature data')

    @patch('fedlearner_webconsole.dataset.apis.datetime')
    def test_post_datasets(self, mock_datetime):
        mock_datetime.now = MagicMock(
            return_value=datetime(2020, 6, 8, 6, 6, 6))
        name = 'test post dataset'
        dataset_type = DatasetType.STREAMING.value
        comment = 'test comment'
        create_response = self.post_helper('/api/v2/datasets',
                                           data={
                                               'name': name,
                                               'dataset_type': dataset_type,
                                               'comment': comment,
                                               'project_id': 1,
                                           })
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_dataset = self.get_response_data(create_response)

        dataset_path = os.path.join(
            tempfile.gettempdir(), 'dataset/20200608_060606_test-post-dataset')
        self.assertEqual(
            {
                'id': 3,
                'name': 'test post dataset',
                'dataset_type': dataset_type,
                'comment': comment,
                'path': dataset_path,
                'created_at': mock.ANY,
                'updated_at': mock.ANY,
                'deleted_at': None,
                'data_batches': [],
                'project_id': 1,
            }, created_dataset)
        # patch datasets
        updated_comment = 'updated comment'
        put_response = self.patch_helper('/api/v2/datasets/3',
                                         data={'comment': updated_comment})
        updated_dataset = self.get_response_data(put_response)
        self.assertEqual(
            {
                'id': 3,
                'name': 'test post dataset',
                'dataset_type': dataset_type,
                'comment': updated_comment,
                'path': dataset_path,
                'created_at': mock.ANY,
                'updated_at': mock.ANY,
                'deleted_at': None,
                'data_batches': [],
                'project_id': 1,
            }, updated_dataset)

    @patch('fedlearner_webconsole.dataset.apis.scheduler.wakeup')
    def test_post_batches(self, mock_wakeup):
        dataset_id = self.default_dataset1.id
        event_time = int(
            datetime(2020, 6, 8, 6, 8, 8, tzinfo=timezone.utc).timestamp())
        files = ['/data/upload/1.csv', '/data/upload/2.csv']
        move = False
        comment = 'test post comment'
        create_response = self.post_helper(
            f'/api/v2/datasets/{dataset_id}/batches',
            data={
                'event_time': event_time,
                'files': files,
                'move': move,
                'comment': comment
            })
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_data_batch = self.get_response_data(create_response)

        self.maxDiff = None
        self.assertEqual(
            {
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
                    'files': [{
                        'destination_path':
                        '/data/dataset/123/batch/20200608_060808/1.csv',
                        'error_message': '',
                        'size': '0',
                        'source_path': '/data/upload/1.csv',
                        'state': 'UNSPECIFIED'
                    }, {
                        'destination_path':
                        '/data/dataset/123/batch/20200608_060808/2.csv',
                        'error_message': '',
                        'size': '0',
                        'source_path': '/data/upload/2.csv',
                        'state': 'UNSPECIFIED'
                    }]
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

        gfile.stat = fake_stat

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
            return FakeFileStatistics(2, 1613982390 * 1e9)
        else:
            return orig_os_stat(path)

    def test_get_default_storage_root(self):
        get_response = self.get_helper('/api/v2/files')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        files = self.get_response_data(get_response)
        self.assertEqual(sorted(files, key=lambda f: f['path']), [
            {
                'path': self._get_temp_path('f1.txt'),
                'size': 2,
                'mtime': 1613982390
            },
            {
                'path': self._get_temp_path('f2.txt'),
                'size': 2,
                'mtime': 1613982390
            },
            {
                'path': self._get_temp_path('s/s3.txt'),
                'size': 2,
                'mtime': 1613982390
            },
        ])

    def test_get_specified_directory(self):
        dir = self._get_temp_path('s')
        get_response = self.get_helper(f'/api/v2/files?directory={dir}')
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        files = self.get_response_data(get_response)
        self.assertEqual(files, [
            {
                'path': self._get_temp_path('s/s3.txt'),
                'size': 2,
                'mtime': 1613982390
            },
        ])


if __name__ == '__main__':
    unittest.main()
