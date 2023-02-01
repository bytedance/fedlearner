#  Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  coding: utf-8

import unittest
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.auth.services import UserService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.audit.models import EventModel, to_model
from fedlearner_webconsole.proto import audit_pb2
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.proto.auth_pb2 import User


def generate_event() -> EventModel:
    return EventModel(name='some_event',
                      user_id=1,
                      resource_type='IAM',
                      resource_name='some_resource',
                      op_type='CREATE',
                      result='SUCCESS',
                      result_code='OK',
                      coordinator_pure_domain_name='bytedance',
                      project_id=1,
                      source='RPC')


class EventModelsTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        events = [generate_event() for _ in range(3)]
        events[1].user_id = None
        events[2].user_id = 0
        with db.session_scope() as session:
            UserService(session).create_user_if_not_exists(username='ada', email='ada@ada.com', password='ada')
            session.add_all(events)
            session.commit()
        self.default_event = audit_pb2.Event(event_id=1,
                                             name='some_event',
                                             user_id=1,
                                             resource_type='IAM',
                                             resource_name='some_resource',
                                             op_type='CREATE',
                                             result='SUCCESS',
                                             result_code='OK',
                                             coordinator_pure_domain_name='bytedance',
                                             project_id=1,
                                             user=User(id=1, username='ada', role='USER'),
                                             created_at=to_timestamp(created_at),
                                             source='RPC')
        self.default_event_2 = audit_pb2.Event(event_id=2,
                                               name='some_event',
                                               user_id=None,
                                               resource_type='IAM',
                                               resource_name='some_resource',
                                               op_type='CREATE',
                                               result='SUCCESS',
                                               result_code='OK',
                                               coordinator_pure_domain_name='bytedance',
                                               project_id=1,
                                               user=None,
                                               created_at=to_timestamp(created_at),
                                               source='RPC')
        self.default_event_3 = audit_pb2.Event(event_id=3,
                                               name='some_event',
                                               user_id=0,
                                               resource_type='IAM',
                                               resource_name='some_resource',
                                               op_type='CREATE',
                                               result='SUCCESS',
                                               result_code='OK',
                                               coordinator_pure_domain_name='bytedance',
                                               project_id=1,
                                               user=None,
                                               created_at=to_timestamp(created_at),
                                               source='RPC')

    def test_uuids(self):
        with db.session_scope() as session:
            events = session.query(EventModel).all()
            self.assertNotEqual(events[0].uuid, events[1].uuid)

    def test_invalid_instances(self):
        event = EventModel()
        with db.session_scope() as session:
            session.add(event)
            self.assertRaises(IntegrityError, session.commit)

    def test_to_proto(self):
        with db.session_scope() as session:
            result = session.query(EventModel).first()
            self.assertDictPartiallyEqual(to_dict(result.to_proto()), to_dict(self.default_event),
                                          ['created_at', 'uuid'])

    def test_save_proto(self):
        with db.session_scope() as session:
            session.add(to_model(self.default_event))
            session.commit()

        with db.session_scope() as session:
            result = session.query(EventModel).get(1)
            self.assertDictPartiallyEqual(to_dict(result.to_proto()), to_dict(self.default_event),
                                          ['created_at', 'uuid'])

    def test_without_user_id_to_proto(self):
        with db.session_scope() as session:
            result = session.query(EventModel).filter_by(user_id=None).first()
            self.assertDictPartiallyEqual(to_dict(result.to_proto()), to_dict(self.default_event_2),
                                          ['created_at', 'uuid'])

    def test_without_user_id_save_proto(self):
        with db.session_scope() as session:
            session.add(to_model(self.default_event_2))
            session.commit()

        with db.session_scope() as session:
            result = session.query(EventModel).get(2)
            self.assertDictPartiallyEqual(to_dict(result.to_proto()), to_dict(self.default_event_2),
                                          ['created_at', 'uuid'])

    def test_user_id_zero_to_proto(self):
        with db.session_scope() as session:
            result = session.query(EventModel).filter_by(user_id=0).first()
            self.assertDictPartiallyEqual(to_dict(result.to_proto()), to_dict(self.default_event_3),
                                          ['created_at', 'uuid'])


if __name__ == '__main__':
    unittest.main()
