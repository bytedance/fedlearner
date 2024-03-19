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
from http import HTTPStatus
from typing import Tuple
from datetime import timedelta, timezone

from dateutil.relativedelta import relativedelta

from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.const import API_VERSION
from fedlearner_webconsole.utils.pp_datetime import to_timestamp, now
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.audit.models import EventModel, to_model
from testing.common import BaseTestCase

PATH_PREFIX = f'{API_VERSION}/events'


def get_times() -> Tuple[int, int]:
    ts = to_timestamp(now())
    return ts - 60 * 2, ts + 60 * 2


def generate_event() -> EventModel:
    return to_model(
        Event(name='some_event',
              user_id=1,
              resource_type=Event.ResourceType.IAM,
              resource_name='some_resource',
              op_type=Event.OperationType.CREATE,
              result=Event.Result.SUCCESS,
              result_code='OK',
              source=Event.Source.UI))


def generate_rpc_event() -> EventModel:
    return to_model(
        Event(name='some_rpc_event',
              user_id=1,
              resource_type=Event.ResourceType.WORKFLOW,
              resource_name='workflow_uuid',
              op_type=Event.OperationType.CREATE,
              result=Event.Result.SUCCESS,
              result_code='OK',
              source=Event.Source.RPC))


class EventApisTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        events = [generate_event() for _ in range(5)]
        with db.session_scope() as session:
            session.bulk_save_objects(events)
            session.commit()

    def test_get_events(self):
        start_time, end_time = get_times()
        self.signin_as_admin()

        response = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{start_time})(end_time<{end_time}))')
        self.assertStatus(response, HTTPStatus.OK)
        self.assertEqual(5, len(self.get_response_data(response)))
        self.assertEqual('CREATE', self.get_response_data(response)[0].get('op_type'))

        response = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="admin")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(0, len(self.get_response_data(response)))

        start_time = to_timestamp(now(timezone.utc) + timedelta(hours=2))
        end_time = to_timestamp(now(timezone.utc) + timedelta(hours=3))

        response = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(0, len(self.get_response_data(response)))

        response = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{end_time})(end_time<{start_time}))')
        self.assertEqual(0, len(self.get_response_data(response)))

    def test_delete_events(self):
        rpc_events = [generate_rpc_event() for _ in range(3)]
        created_at = now(timezone.utc) - relativedelta(months=8)
        with db.session_scope() as session:
            session.bulk_save_objects(rpc_events)
            session.query(EventModel).update({'created_at': created_at})
            session.commit()
        start_time, end_time = get_times()

        self.signin_as_admin()
        response = self.delete_helper(f'{PATH_PREFIX}?event_type=USER_ENDPOINT')
        self.assertStatus(response, HTTPStatus.NO_CONTENT)

        start_time = to_timestamp(now(timezone.utc) - relativedelta(months=9))
        end_time = to_timestamp(now(timezone.utc) - relativedelta(months=7))

        response = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(3, len(self.get_response_data(response)))

    def test_delete_rpc_events(self):
        rpc_events = [generate_rpc_event() for _ in range(3)]
        created_at = now(timezone.utc) - relativedelta(months=8)
        with db.session_scope() as session:
            session.bulk_save_objects(rpc_events)
            session.query(EventModel).update({'created_at': created_at})
            session.commit()

        start_time, end_time = get_times()

        self.signin_as_admin()
        response = self.delete_helper(f'{PATH_PREFIX}?event_type=RPC')
        self.assertStatus(response, HTTPStatus.NO_CONTENT)

        start_time = to_timestamp(now(timezone.utc) - relativedelta(months=9))
        end_time = to_timestamp(now(timezone.utc) - relativedelta(months=7))

        response = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{start_time})(end_time<{end_time}))')
        self.assertEqual(5, len(self.get_response_data(response)))

    def test_get_with_op_type(self):
        start_time, end_time = get_times()

        self.signin_as_admin()
        resp = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{start_time})(end_time<{end_time})(op_type="CREATE"))'  # pylint: disable=line-too-long
        )
        self.assertEqual(5, len(self.get_response_data(resp)))

        resp = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{end_time})(end_time<{start_time})(op_type="UPDATE"))'  # pylint: disable=line-too-long
        )
        self.assertEqual(0, len(self.get_response_data(resp)))

        resp = self.get_helper(
            f'{PATH_PREFIX}?filter=(and(username="ada")(start_time>{end_time})(end_time<{start_time})(op_type="poop"))')
        self.assert200(resp)
        self.assertEqual(0, len(self.get_response_data(resp)))


if __name__ == '__main__':
    unittest.main()
