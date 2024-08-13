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
from unittest.mock import patch, MagicMock, call
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import review_pb2
from fedlearner_webconsole.review.runners import TicketHelperRunner
from fedlearner_webconsole.composer.context import RunnerContext, RunnerInput
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus


class TicketHelperRunnerTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.review.runners.ReviewServiceClient')
    def test_run(self, mock_review_service_client: MagicMock):
        with db.session_scope() as session:
            session.add(
                Participant(id=111,
                            name='p1',
                            domain_name='fl-test1.com',
                            ticket_status=TicketStatus.PENDING,
                            ticket_uuid='u12345'))
            session.add(
                Participant(id=222,
                            name='p2',
                            domain_name='fl-test2.com',
                            ticket_status=TicketStatus.APPROVED,
                            ticket_uuid='u22345'))
            session.add(
                Participant(id=333,
                            name='p3',
                            domain_name='fl-test3.com',
                            ticket_status=TicketStatus.DECLINED,
                            ticket_uuid='u32345'))
            session.add(
                Participant(id=444,
                            name='p1',
                            domain_name='fl-test4.com',
                            ticket_status=TicketStatus.PENDING,
                            ticket_uuid='u42345'))
            session.commit()

        client = MagicMock()
        mock_review_service_client.from_participant.return_value = client
        client.get_ticket.side_effect = [
            review_pb2.Ticket(status=review_pb2.ReviewStatus.APPROVED),
            review_pb2.Ticket(status=review_pb2.ReviewStatus.PENDING)
        ]

        runner = TicketHelperRunner(domain_name='fl-central.com')
        _, output = runner.run(RunnerContext(0, RunnerInput()))

        mock_review_service_client.from_participant.assert_called_with(domain_name='fl-central.com')
        client.get_ticket.assert_has_calls(calls=[call('u12345'), call('u42345')])
        self.assertEqual(output.ticket_helper_output.updated_ticket['CREATE_PARTICIPANT'].ids, [111])
        self.assertEqual(output.ticket_helper_output.unupdated_ticket['CREATE_PARTICIPANT'].ids, [444])


if __name__ == '__main__':
    unittest.main()
