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
from fedlearner_webconsole.cleanup.models import Cleanup, CleanupState, ResourceType
from fedlearner_webconsole.proto.cleanup_pb2 import CleanupPayload, CleanupPb
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


class CleanupTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        self.default_paylaod = CleanupPayload(paths=['/Major333/test_path/a.csv'])
        default_cleanup = Cleanup(id=1,
                                  state=CleanupState.WAITING,
                                  created_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                  updated_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                  target_start_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                  resource_id=100,
                                  resource_type=ResourceType.DATASET.name,
                                  payload=self.default_paylaod)
        cleanup_without_resource = Cleanup(id=2,
                                           state=CleanupState.WAITING,
                                           created_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                           updated_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                           target_start_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                           resource_id=100,
                                           resource_type=ResourceType.NO_RESOURCE.name,
                                           payload=self.default_paylaod)
        running_cleanup = Cleanup(id=3,
                                  state=CleanupState.RUNNING,
                                  created_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                  updated_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                  target_start_at=datetime(2022, 2, 22, tzinfo=timezone.utc),
                                  resource_id=100,
                                  resource_type=ResourceType.NO_RESOURCE.name,
                                  payload=self.default_paylaod)
        with db.session_scope() as session:
            session.add(default_cleanup)
            session.add(cleanup_without_resource)
            session.add(running_cleanup)
            session.commit()

    def test_payload(self):
        with db.session_scope() as session:
            cleanup = session.query(Cleanup).get(1)
            self.assertEqual(cleanup.payload, self.default_paylaod)
            cleanup.payload = CleanupPayload(paths=['/Major333/test_path/b.csv'])
            session.add(cleanup)
            session.commit()
        with db.session_scope() as session:
            cleanup = session.query(Cleanup).get(1)
            self.assertEqual(['/Major333/test_path/b.csv'], cleanup.payload.paths)

    def test_cancellable(self):
        with db.session_scope() as session:
            default_cleanup = session.query(Cleanup).get(1)
            cleanup_without_resource = session.query(Cleanup).get(2)
            running_cleanup = session.query(Cleanup).get(3)
            self.assertTrue(default_cleanup.is_cancellable)
            self.assertTrue(cleanup_without_resource.is_cancellable)
            self.assertFalse(running_cleanup.is_cancellable)

    def test_to_proto(self):
        expected_cleanup_proto = CleanupPb(id=1,
                                           state='WAITING',
                                           target_start_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc)),
                                           resource_id=100,
                                           resource_type='DATASET',
                                           payload=self.default_paylaod,
                                           updated_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc)),
                                           created_at=to_timestamp(datetime(2022, 2, 22, tzinfo=timezone.utc)))
        with db.session_scope() as session:
            cleanup_proto = session.query(Cleanup).get(1).to_proto()
            self.assertEqual(cleanup_proto, expected_cleanup_proto)


if __name__ == '__main__':
    unittest.main()
