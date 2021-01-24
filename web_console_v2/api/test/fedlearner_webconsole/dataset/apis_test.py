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

import json
import datetime
import unittest
from http import HTTPStatus

from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import (Dataset, DatasetType,
                                                  DataBatch)


class DatasetApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.default_dataset = Dataset()
        self.default_dataset.name = 'default_dataset'
        self.default_dataset.type = DatasetType.STREAMING
        self.default_dataset.comment = 'test comment'
        db.session.add(self.default_dataset)
        db.session.commit()

    def test_post_dataset(self):
        name = 'test_post_dataset'
        dataset_type = DatasetType.STREAMING.value
        comment = 'test comment'
        create_response = self.client.post(
            '/api/v2/datasets',
            data=json.dumps({
                'name': name,
                'type': dataset_type,
                'comment': comment
            }),
            content_type='application/json')
        self.assertEqual(create_response.status_code, HTTPStatus.OK)
        created_dataset = json.loads(create_response.data).get('data')

        queried_dataset = Dataset.query.filter_by(
            id=created_dataset.get('id')).first()
        self.assertEqual(created_dataset, queried_dataset.to_dict())

    def test_post_data_batch(self):
        dataset_id = self.default_dataset.id
        event_time = int(datetime.datetime.now().timestamp())
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
        created_data_batch = json.loads(create_response.data).get('data')

        queried_data_batch = DataBatch.query.filter_by(
            event_time=datetime.datetime.fromtimestamp(event_time),
            dataset_id=dataset_id).first()
        self.assertEqual(created_data_batch, queried_data_batch.to_dict())


if __name__ == '__main__':
    unittest.main()
