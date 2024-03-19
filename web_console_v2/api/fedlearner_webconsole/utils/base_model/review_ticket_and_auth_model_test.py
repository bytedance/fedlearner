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
from unittest.mock import MagicMock, patch

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.utils.base_model.review_ticket_and_auth_model import ReviewTicketAndAuthModel, \
    AuthFrontendState
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto import project_pb2


class TestModel(db.Model, ReviewTicketAndAuthModel):
    __tablename__ = 'test_model'
    __table_args__ = (default_table_args('This is webconsole test_model table'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)


class ReviewTicketAndAuthModelTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            model = TestModel(auth_status=AuthStatus.PENDING)
            session.add(model)
            session.commit()

    @patch(
        'fedlearner_webconsole.utils.base_model.review_ticket_and_auth_model.ReviewTicketAndAuthModel.' \
            'is_all_participants_authorized'
    )
    def test_auth_frontend_state(self, mock_authorized: MagicMock):
        with db.session_scope() as session:
            test_model: TestModel = session.query(TestModel).get(1)
            mock_authorized.return_value = True
            self.assertEqual(test_model.auth_frontend_state, AuthFrontendState.AUTH_APPROVED)

            mock_authorized.return_value = False
            self.assertEqual(test_model.auth_frontend_state, AuthFrontendState.AUTH_PENDING)

            test_model.ticket_status = TicketStatus.PENDING
            self.assertEqual(test_model.auth_frontend_state, AuthFrontendState.TICKET_PENDING)

            test_model.ticket_status = TicketStatus.DECLINED
            self.assertEqual(test_model.auth_frontend_state, AuthFrontendState.TICKET_DECLINED)

    def test_set_and_get_participants_info(self):
        participants_info = project_pb2.ParticipantsInfo(
            participants_map={
                'test_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                'test_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
            })
        with db.session_scope() as session:
            test_model = session.query(TestModel).get(1)
            test_model.set_participants_info(participants_info)
            session.commit()
        with db.session_scope() as session:
            test_model = session.query(TestModel).get(1)
            self.assertEqual(test_model.get_participants_info(), participants_info)

    def test_is_all_participants_authorized(self):
        # test no participants_info
        with db.session_scope() as session:
            test_model = session.query(TestModel).get(1)
            self.assertTrue(test_model.is_all_participants_authorized())

        # test all authorized
        participants_info = project_pb2.ParticipantsInfo(
            participants_map={
                'test_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name),
                'test_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
            })
        with db.session_scope() as session:
            test_model = session.query(TestModel).get(1)
            test_model.set_participants_info(participants_info)
            self.assertTrue(test_model.is_all_participants_authorized())

        # test not all authorized
        participants_info = project_pb2.ParticipantsInfo(
            participants_map={
                'test_1': project_pb2.ParticipantInfo(auth_status=AuthStatus.PENDING.name),
                'test_2': project_pb2.ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name)
            })
        with db.session_scope() as session:
            test_model = session.query(TestModel).get(1)
            test_model.set_participants_info(participants_info)
            self.assertFalse(test_model.is_all_participants_authorized())


if __name__ == '__main__':
    unittest.main()
