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
import urllib.parse
from http import HTTPStatus
from datetime import datetime, timezone
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.cleanup.models import ResourceType, CleanupState, Cleanup
from fedlearner_webconsole.dataset.models import Dataset, DatasetKindV2, DatasetType
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupPayload, CleanupPb
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.proto import to_dict


class CleanupsApiTest(BaseTestCase):
    _TARGET_START_AT = datetime(2022, 2, 22, 10, 10, 12, tzinfo=timezone.utc)
    _CREATED_AT = datetime(2022, 2, 22, 3, 3, 4, tzinfo=timezone.utc)
    _CREATED_AT_2 = datetime(2022, 3, 22, 3, 3, 4, tzinfo=timezone.utc)

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        dataset1 = Dataset(id=1,
                           name='default_dataset',
                           dataset_type=DatasetType.PSI,
                           project_id=1,
                           dataset_kind=DatasetKindV2.RAW,
                           path='/data/default_dataset/')
        self.default_paylaod = CleanupPayload(paths=['/Major333/test_path/a.csv'])
        cleanup1 = Cleanup(id=1,
                           state=CleanupState.WAITING,
                           created_at=self._CREATED_AT,
                           updated_at=self._CREATED_AT,
                           target_start_at=self._TARGET_START_AT,
                           resource_id=dataset1.id,
                           resource_type=ResourceType(Dataset).name,
                           payload=self.default_paylaod)
        cleanup2 = Cleanup(id=2,
                           state=CleanupState.CANCELED,
                           created_at=self._CREATED_AT,
                           updated_at=self._CREATED_AT,
                           target_start_at=self._TARGET_START_AT,
                           resource_id=dataset1.id,
                           resource_type=ResourceType(Dataset).name,
                           payload=self.default_paylaod)
        with db.session_scope() as session:
            session.add(dataset1)
            session.add(cleanup1)
            session.add(cleanup2)
            session.commit()
        self.signin_as_admin()

    def test_get_without_filter_and_pagination(self):
        response = self.get_helper('/api/v2/cleanups')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 2)

    def test_get_with_pagination(self):
        response = self.get_helper('/api/v2/cleanups?page=1&page_size=1')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 1)

    def test_get_with_invalid_filter(self):
        response = self.get_helper('/api/v2/cleanups?filter=invalid')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_with_filter(self):
        filter_exp = urllib.parse.quote('(and(resource_type="DATASET")(state="WAITING"))')
        response = self.get_helper(f'/api/v2/cleanups?filter={filter_exp}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = self.get_response_data(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], 1)


class CleanupApiTest(BaseTestCase):
    _TARGET_START_AT = datetime(2022, 2, 22, 10, 10, 12, tzinfo=timezone.utc)
    _CREATED_AT = datetime(2022, 2, 22, 3, 3, 4, tzinfo=timezone.utc)

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        dataset1 = Dataset(id=1,
                           name='default_dataset',
                           dataset_type=DatasetType.PSI,
                           project_id=1,
                           dataset_kind=DatasetKindV2.RAW,
                           path='/data/default_dataset/')
        self.default_paylaod = CleanupPayload(paths=['/Major333/test_path/a.csv'])
        cleanup1 = Cleanup(id=1,
                           state=CleanupState.WAITING,
                           created_at=self._CREATED_AT,
                           updated_at=self._CREATED_AT,
                           target_start_at=self._TARGET_START_AT,
                           resource_id=dataset1.id,
                           resource_type=ResourceType(Dataset).name,
                           payload=self.default_paylaod)
        with db.session_scope() as session:
            session.add(dataset1)
            session.add(cleanup1)
            session.commit()

    def test_get(self):
        expected_cleanup_proto = CleanupPb(id=1,
                                           state='WAITING',
                                           completed_at=None,
                                           resource_id=1,
                                           resource_type='DATASET',
                                           payload=self.default_paylaod,
                                           target_start_at=to_timestamp(self._TARGET_START_AT),
                                           updated_at=to_timestamp(self._CREATED_AT),
                                           created_at=to_timestamp(self._CREATED_AT))
        self.signin_as_admin()
        response = self.get_helper(f'/api/v2/cleanups/{expected_cleanup_proto.id}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        cleanup = self.get_response_data(response)
        self.assertEqual(cleanup, to_dict(expected_cleanup_proto))


class CleanupCancelApiTest(BaseTestCase):
    _TARGET_START_AT = datetime(2022, 2, 22, 10, 10, 12, tzinfo=timezone.utc)
    _CREATED_AT = datetime(2022, 2, 22, 3, 3, 4, tzinfo=timezone.utc)

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    def setUp(self):
        super().setUp()
        dataset1 = Dataset(id=1,
                           name='default_dataset',
                           dataset_type=DatasetType.PSI,
                           project_id=1,
                           dataset_kind=DatasetKindV2.RAW,
                           path='/data/default_dataset/')
        self.default_payload = CleanupPayload(paths=['/Major333/test_path/a.csv'])
        cleanup1 = Cleanup(id=1,
                           state=CleanupState.WAITING,
                           created_at=self._CREATED_AT,
                           updated_at=self._CREATED_AT,
                           target_start_at=self._TARGET_START_AT,
                           resource_id=dataset1.id,
                           resource_type=ResourceType(Dataset).name,
                           payload=self.default_payload)
        with db.session_scope() as session:
            session.add(dataset1)
            session.add(cleanup1)
            session.commit()

    def test_cleanup_waiting_cancel(self):
        self.signin_as_admin()
        response = self.post_helper('/api/v2/cleanups/1:cancel', {})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.get_helper('/api/v2/cleanups/1')
        cancelled_cleanup = self.get_response_data(response)
        self.assertEqual(cancelled_cleanup['state'], 'CANCELED')


if __name__ == '__main__':
    unittest.main()
