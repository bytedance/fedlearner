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
from typing import Tuple

from fedlearner_webconsole.audit.services import EventService
from fedlearner_webconsole.audit.models import EventModel
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.utils.filtering import parse_expression
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterExpressionKind, SimpleExpression, FilterOp
from fedlearner_webconsole.auth.services import UserService

from testing.no_web_server_test_case import NoWebServerTestCase


def get_times() -> Tuple[int, int]:
    ts = to_timestamp(now())
    return ts - 60 * 2, ts + 60 * 2


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


class EventServiceTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            UserService(session).create_user_if_not_exists(username='ada', email='ada@ada.com', password='ada')
            event_1 = generate_event()
            event_1.coordinator_pure_domain_name = 'mihoyo'
            session.add(event_1)
            event_2 = generate_event()
            event_2.resource_type = 'WORKFLOW'
            event_2.op_type = 'UPDATE'
            session.add(event_2)
            event_3 = generate_event()
            event_3.resource_type = 'DATASET'
            event_3.op_type = 'DELETE'
            event_3.result_code = 'CANCELLED'
            session.add(event_3)
            session.commit()

    def test_emit_event(self):
        with db.session_scope() as session:
            service = EventService(session)
            event = generate_event()
            event_param = Event(name=event.name,
                                user_id=event.user_id,
                                resource_type=event.resource_type,
                                resource_name=event.resource_name,
                                result_code=event.result_code,
                                coordinator_pure_domain_name=event.coordinator_pure_domain_name,
                                project_id=event.project_id,
                                op_type=event.op_type,
                                result=event.result,
                                source=event.source)
            service.emit_event(event_param)
            session.commit()
            events = service.get_events()
            self.assertEqual(4, len(events.all()))
            self.assertEqual(now().hour, events.first().created_at.hour)

    def test_get_events(self):
        with db.session_scope() as session:
            service = EventService(session)
            events = service.get_events()

        self.assertEqual(3, len(events.all()))

    def test_get_rpc_events_with_filter(self):
        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='coordinator_pure_domain_name',
                                          op=FilterOp.CONTAIN,
                                          string_value='mihoyo',
                                      ))
        with db.session_scope() as session:
            service = EventService(session)
            events = service.get_events(filter_exp)
            self.assertEqual(1, len(events.all()))
            self.assertEqual(events[0].coordinator_pure_domain_name, 'mihoyo')

        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='op_type',
                                          op=FilterOp.IN,
                                          list_value=SimpleExpression.ListValue(string_list=['UPDATE', 'DELETE'])))
        with db.session_scope() as session:
            service = EventService(session)
            events = service.get_events(filter_exp)
            self.assertEqual(2, len(events.all()))
            self.assertEqual(events[0].op_type, 'DELETE')
            self.assertEqual(events[1].op_type, 'UPDATE')

        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='op_type',
                                          op=FilterOp.EQUAL,
                                          string_value='UPDATE',
                                      ))
        with db.session_scope() as session:
            service = EventService(session)
            events = service.get_events(filter_exp)
            self.assertEqual(1, len(events.all()))
            self.assertEqual(events[0].op_type, 'UPDATE')

        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='result_code',
                                          op=FilterOp.EQUAL,
                                          string_value='CANCELLED',
                                      ))
        with db.session_scope() as session:
            service = EventService(session)
            events = service.get_events(filter_exp)
            self.assertEqual(1, len(events.all()))
            self.assertEqual(events[0].result_code, 'CANCELLED')

        filter_exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                      simple_exp=SimpleExpression(
                                          field='resource_type',
                                          op=FilterOp.IN,
                                          list_value=SimpleExpression.ListValue(string_list=['WORKFLOW', 'DATASET'])))
        with db.session_scope() as session:
            service = EventService(session)
            events = service.get_events(filter_exp)
            self.assertEqual(2, len(events.all()))
            self.assertEqual(events[0].resource_type, 'DATASET')
            self.assertEqual(events[1].resource_type, 'WORKFLOW')

    def test_delete_events(self):
        with db.session_scope() as session:
            service = EventService(session)
            start_time, end_time = get_times()
            filter_exp = parse_expression(f'(and(start_time>{start_time})(end_time<{end_time}))')
            self.assertIsNone(service.delete_events(filter_exp))
            self.assertEqual(0, service.get_events().count())


if __name__ == '__main__':
    unittest.main()
