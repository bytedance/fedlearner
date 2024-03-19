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
from datetime import datetime, timezone
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.cleanup.services import CleanupService
from fedlearner_webconsole.cleanup.models import Cleanup, CleanupState, ResourceType
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupPayload, CleanupParameter, CleanupPb
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterExpressionKind, SimpleExpression, FilterOp
from fedlearner_webconsole.dataset.models import Dataset, DatasetType, DatasetKindV2
from fedlearner_webconsole.utils.resource_name import resource_uuid


class CleanupServiceTest(NoWebServerTestCase):
    _TARGET_START_AT = datetime(2022, 2, 22, 10, 10, 12, tzinfo=timezone.utc)
    _CREATED_AT = datetime(2022, 2, 22, 3, 3, 4, tzinfo=timezone.utc)

    def setUp(self):
        super().setUp()
        self.default_paylaod = CleanupPayload(paths=['/Major333/test_path/a.csv'])
        self.deafult_dataset = Dataset(
            id=100,
            uuid=resource_uuid(),
            name='dataset_1',
            dataset_type=DatasetType.PSI,
            project_id=100,
            dataset_kind=DatasetKindV2.RAW,
            path='/data/dataset_1/',
        )
        default_cleanup = Cleanup(id=1,
                                  state=CleanupState.WAITING,
                                  created_at=self._CREATED_AT,
                                  updated_at=self._CREATED_AT,
                                  target_start_at=self._TARGET_START_AT,
                                  resource_id=100,
                                  resource_type=ResourceType.DATASET.name,
                                  payload=self.default_paylaod)
        default_cleanup_2 = Cleanup(id=2,
                                    state=CleanupState.WAITING,
                                    created_at=self._CREATED_AT,
                                    updated_at=self._CREATED_AT,
                                    target_start_at=self._TARGET_START_AT,
                                    resource_id=100,
                                    resource_type=ResourceType.NO_RESOURCE.name,
                                    payload=self.default_paylaod)
        with db.session_scope() as session:
            session.add(self.deafult_dataset)
            session.add(default_cleanup)
            session.add(default_cleanup_2)
            session.commit()

    def test_get_cleanups(self):
        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='state',
                                          op=FilterOp.EQUAL,
                                          string_value='WAITING',
                                      ))
        with db.session_scope() as session:
            service = CleanupService(session)
            paginations = service.get_cleanups(filter_exp=filter_exp, page=1, page_size=2)
            cleanup_ids = [cleanup.id for cleanup in paginations.get_items()]
            self.assertEqual(cleanup_ids, [1, 2])

    def test_get_cleanup(self):
        expected_cleanup_display_proto = CleanupPb(id=1,
                                                   state='WAITING',
                                                   target_start_at=to_timestamp(self._TARGET_START_AT),
                                                   resource_id=100,
                                                   resource_type='DATASET',
                                                   payload=self.default_paylaod,
                                                   updated_at=to_timestamp(self._CREATED_AT),
                                                   created_at=to_timestamp(self._CREATED_AT))
        with db.session_scope() as session:
            service = CleanupService(session)
            cleanup = service.get_cleanup(cleanup_id=1)
            self.assertEqual(cleanup, expected_cleanup_display_proto)

    def test_get_cleanup_without_resource_type(self):
        expected_cleanup_display_proto = CleanupPb(id=2,
                                                   state='WAITING',
                                                   target_start_at=to_timestamp(self._TARGET_START_AT),
                                                   resource_id=100,
                                                   resource_type='NO_RESOURCE',
                                                   payload=self.default_paylaod,
                                                   updated_at=to_timestamp(self._CREATED_AT),
                                                   created_at=to_timestamp(self._CREATED_AT))
        with db.session_scope() as session:
            service = CleanupService(session)
            cleanup = service.get_cleanup(cleanup_id=2)
            self.assertEqual(cleanup, expected_cleanup_display_proto)

    def test_create_cleanup(self):
        cleanup_parm = CleanupParameter(resource_id=1011,
                                        resource_type='DATASET',
                                        target_start_at=to_timestamp(self._TARGET_START_AT),
                                        payload=self.default_paylaod)
        with db.session_scope() as session:
            cleanup = CleanupService(session).create_cleanup(cleanup_parm)
            session.commit()
            cleanup_id = cleanup.id
        with db.session_scope() as session:
            created_cleanup: Cleanup = session.query(Cleanup).get(cleanup_id)
            self.assertEqual(created_cleanup.resource_type, ResourceType.DATASET)
            self.assertEqual(created_cleanup.resource_id, 1011)
            self.assertEqual(to_timestamp(created_cleanup.target_start_at), to_timestamp(self._TARGET_START_AT))
            self.assertEqual(created_cleanup.payload, self.default_paylaod)

    def test_cancel_cleanup_by_id(self):
        with db.session_scope() as session:
            service = CleanupService(session)
            service.cancel_cleanup_by_id(1)
            session.commit()
        with db.session_scope() as session:
            cleanup = session.query(Cleanup).get(1)
            self.assertEqual(cleanup.state, CleanupState.CANCELED)


if __name__ == '__main__':
    unittest.main()
