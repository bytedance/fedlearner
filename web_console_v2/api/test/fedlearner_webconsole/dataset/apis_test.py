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
import json
import time
import shutil
import glob
import datetime
from http import HTTPStatus
from testing.common import BaseTestCase
from fedlearner_webconsole.dataset.models import (BatchState, DatasetType,
                                                  DataBatch)
from fedlearner_webconsole.utils.file_manager import FileManager


class DatasetApiTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        os.environ['STORAGE_ROOT_PATH'] = os.getcwd()
        os.environ['DATASET_UPLOAD_PATH'] = os.getcwd()
        for i in range(10):
            with open('20210101_{}'.format(i), 'w') as file:
                for _ in range(1000):
                    for _ in range(100):
                        file.write('1234567890')
                    file.write('\n')

    def tearDown(self):
        for file_name in glob.glob(os.path.join(os.getcwd(), '20210101*')):
            os.remove(file_name)
        shutil.rmtree(os.path.join(os.environ['STORAGE_ROOT_PATH'], 'dataset'))
        del os.environ['STORAGE_ROOT_PATH']
        del os.environ['DATASET_UPLOAD_PATH']

    def test_post_dataset(self):
        name = 'test'
        dataset_type = DatasetType.STREAMING.value
        source = {
            'event_time': 1608184739,
            'file': [os.path.join(os.environ['DATASET_UPLOAD_PATH'],
                                  '20210101_{}'.format(i)) for i in range(10)]
        }
        comment = 'test'
        create_response = self.client.post(
            '/api/v2/datasets',
            data=json.dumps({
                'name': name,
                'type': dataset_type,
                'data_batch': source,
                'copy': False,
                'comment': comment
            }),
            content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_dataset = json.loads(create_response.data)
        print('Sleep 3s to wait for import finishing...')
        time.sleep(3)
        created_batch = created_dataset.get('data').get('data_batches')[0]
        queried_batch = DataBatch.query\
            .filter_by(dataset_id=created_batch.get('dataset_id'),
                       event_time=datetime.datetime
                       .fromtimestamp(created_batch.get('event_time'))).all()
        batch_storage_path = os.path.join(os.environ['STORAGE_ROOT_PATH'],
                                          'dataset')
        self.assertEqual(len(queried_batch), 1)
        self.assertEqual(queried_batch[0].state, BatchState.SUCCESS)
        # count file size
        dataset_size = 0
        for root, batches, files in os.walk(batch_storage_path):
            for file in files:
                dataset_size += os.path.getsize(
                    os.path.join(root, file))
        self.assertEqual(len(FileManager().ls(batch_storage_path, True)),
                         queried_batch[0].file_num)
        self.assertEqual(dataset_size, queried_batch[0].file_size)
