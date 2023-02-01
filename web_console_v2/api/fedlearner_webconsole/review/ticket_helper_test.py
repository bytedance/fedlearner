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

import logging
import unittest
from unittest.mock import call, patch, MagicMock
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.review.common import NO_CENTRAL_SERVER_UUID
from fedlearner_webconsole.review.ticket_helper import (NoCenterServerTicketHelper, CenterServerTicketHelper,
                                                        get_ticket_helper)
from fedlearner_webconsole.proto import review_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.utils.base_model.review_ticket_model import ReviewTicketModel, TicketStatus
from testing.common import NoWebServerTestCase


class FakeModel(db.Model, ReviewTicketModel):
    __tablename__ = 'fake_model'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    uuid = db.Column(db.String(255), nullable=True, comment='uuid')


class NoCenterServerTicketHelperTest(NoWebServerTestCase):

    def test_get_ticket(self):
        with db.session_scope() as session:
            ticket = NoCenterServerTicketHelper(session).get_ticket(uuid='u12345')
            self.assertEqual(
                ticket,
                review_pb2.Ticket(uuid='u12345',
                                  type=review_pb2.TicketType.UNKOWN_TYPE,
                                  status=review_pb2.ReviewStatus.APPROVED,
                                  review_strategy=review_pb2.ReviewStrategy.AUTO))

    @patch('fedlearner_webconsole.review.common.REVIEW_ORM_MAPPER',
           {review_pb2.TicketType.CREATE_PARTICIPANT: FakeModel})
    def test_create_ticket(self):
        with db.session_scope() as session:
            self.assertRaises(InvalidArgumentException,
                              NoCenterServerTicketHelper(session).create_ticket,
                              ticket_type=review_pb2.TicketType.CREATE_NODE,
                              details=review_pb2.TicketDetails(uuid='u1234'))

        with db.session_scope() as session:
            fake_data = FakeModel(uuid='u1234')
            session.add(fake_data)
            session.flush()
            ticket = NoCenterServerTicketHelper(session).create_ticket(
                ticket_type=review_pb2.TicketType.CREATE_PARTICIPANT, details=review_pb2.TicketDetails(uuid='u1234'))
            session.flush()
            self.assertEqual(fake_data.ticket_status, TicketStatus.APPROVED)
            session.commit()
        with db.session_scope() as session:
            resource = session.query(FakeModel).filter_by(uuid='u1234').first()
            self.assertEqual(resource.ticket_status, TicketStatus.APPROVED)
            self.assertEqual(resource.ticket_uuid, NO_CENTRAL_SERVER_UUID)
            self.assertEqual(
                ticket,
                review_pb2.Ticket(uuid=NO_CENTRAL_SERVER_UUID,
                                  type=review_pb2.TicketType.CREATE_PARTICIPANT,
                                  details=review_pb2.TicketDetails(uuid='u1234'),
                                  status=review_pb2.ReviewStatus.APPROVED,
                                  review_strategy=review_pb2.ReviewStrategy.AUTO))

    def test_validate_ticket(self):
        with db.session_scope() as session:
            # ignore validate_fn, because center server is not configured.
            validate_fn = lambda _: False
            self.assertFalse(NoCenterServerTicketHelper(session).validate_ticket('u1234', validate_fn))
            self.assertTrue(NoCenterServerTicketHelper(session).validate_ticket(NO_CENTRAL_SERVER_UUID, validate_fn))


class CenterServerTicketHelperTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.review.ticket_helper.ReviewServiceClient')
    def test_validate_ticket(self, mock_review_service_client: MagicMock):
        client = MagicMock()
        mock_review_service_client.from_participant.return_value = client
        client.get_ticket.side_effect = [
            review_pb2.Ticket(uuid='u1234',
                              status=review_pb2.ReviewStatus.APPROVED,
                              details=review_pb2.TicketDetails(uuid='u1234')),
            review_pb2.Ticket(uuid='u234',
                              status=review_pb2.ReviewStatus.APPROVED,
                              details=review_pb2.TicketDetails(uuid='u2345')),
            review_pb2.Ticket(uuid='u1234',
                              status=review_pb2.ReviewStatus.APPROVED,
                              details=review_pb2.TicketDetails(uuid='u2345')),
        ]

        with db.session_scope() as session:
            validate_fn = lambda t: t.details.uuid == 'u2345'
            self.assertFalse(CenterServerTicketHelper(session, 'fl-central.com').validate_ticket('u1234', validate_fn))
            self.assertFalse(CenterServerTicketHelper(session, 'fl-central.com').validate_ticket('u1234', validate_fn))
            self.assertTrue(CenterServerTicketHelper(session, 'fl-central.com').validate_ticket('u1234', validate_fn))

        mock_review_service_client.from_participant.assert_called_with(domain_name='fl-central.com')
        client.get_ticket.assert_has_calls(calls=[call('u1234'), call('u1234'), call('u1234')])

    @patch('fedlearner_webconsole.review.common.REVIEW_ORM_MAPPER',
           {review_pb2.TicketType.CREATE_PARTICIPANT: FakeModel})
    @patch('fedlearner_webconsole.review.ticket_helper.get_current_user', lambda: User(username='creator'))
    @patch('fedlearner_webconsole.review.ticket_helper.ReviewServiceClient')
    def test_create_ticket(self, mock_review_service_client: MagicMock):
        with db.session_scope() as session:
            self.assertRaises(InvalidArgumentException,
                              CenterServerTicketHelper(session, 'fl-central').create_ticket,
                              ticket_type=review_pb2.TicketType.CREATE_NODE,
                              details=review_pb2.TicketDetails(uuid='u1234'))

        client = MagicMock()
        mock_review_service_client.from_participant.return_value = client
        client.create_ticket.return_value = review_pb2.Ticket(uuid='u4321',
                                                              status=review_pb2.ReviewStatus.PENDING,
                                                              details=review_pb2.TicketDetails(uuid='u1234'))

        with db.session_scope() as session:
            fake_data = FakeModel(uuid='u1234')
            session.add(fake_data)
            session.flush()
            CenterServerTicketHelper(session, 'fl-central.com').create_ticket(
                ticket_type=review_pb2.TicketType.CREATE_PARTICIPANT, details=review_pb2.TicketDetails(uuid='u1234'))
            session.flush()
            self.assertEqual(fake_data.ticket_status, TicketStatus.PENDING)
            session.commit()

        with db.session_scope() as session:
            resource = session.query(FakeModel).filter_by(uuid='u1234').first()
            self.assertEqual(resource.ticket_status, TicketStatus.PENDING)
            self.assertEqual(resource.ticket_uuid, 'u4321')

        mock_review_service_client.from_participant.assert_called_with(domain_name='fl-central.com')
        self.assertEqual([call[0][1] for call in client.create_ticket.call_args_list][0], 'creator')


class GetTicketHelperTest(unittest.TestCase):

    @patch('fedlearner_webconsole.flag.models.Flag.REVIEW_CENTER_CONFIGURATION.value', '{}')
    def test_no_center_server(self):
        with db.session_scope() as session:
            self.assertIsInstance(get_ticket_helper(session), NoCenterServerTicketHelper)

    @patch('fedlearner_webconsole.flag.models.Flag.REVIEW_CENTER_CONFIGURATION.value',
           '{"domain_name": "fl-central.com"}')
    def test_with_center_server(self):
        with db.session_scope() as session:
            self.assertIsInstance(get_ticket_helper(session), CenterServerTicketHelper)

    @patch('fedlearner_webconsole.flag.models.Flag.REVIEW_CENTER_CONFIGURATION.value', '{"dom_name": "fl-central.com"}')
    def test_with_invalid_center_server(self):
        with db.session_scope() as session:
            self.assertRaises(KeyError, get_ticket_helper, session)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
