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
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.utils.base_model.review_ticket_model import ReviewTicketModel, TicketStatus
from fedlearner_webconsole.db import db, default_table_args


class TestModel(db.Model, ReviewTicketModel):
    __tablename__ = 'test_model'
    __table_args__ = (default_table_args('This is webconsole dataset table'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)


class ReviewTicketModelTest(NoWebServerTestCase):

    def test_mixins(self):
        with db.session_scope() as session:
            model = TestModel(ticket_uuid='u1234', ticket_status=TicketStatus.APPROVED)
            session.add(model)
            session.commit()
        with db.session_scope() as session:
            models = session.query(TestModel).all()
            self.assertEqual(len(models), 1)
            self.assertEqual(models[0].ticket_status, TicketStatus.APPROVED)
            self.assertEqual(models[0].ticket_uuid, 'u1234')


if __name__ == '__main__':
    unittest.main()
