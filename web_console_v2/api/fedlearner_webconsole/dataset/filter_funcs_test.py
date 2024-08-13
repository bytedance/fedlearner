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
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.filter_funcs import dataset_format_filter_op_equal, dataset_format_filter_op_in, \
    dataset_publish_frontend_filter_op_equal, dataset_auth_status_filter_op_in
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.proto.filtering_pb2 import SimpleExpression


class FilterFuncsTest(NoWebServerTestCase):

    def test_dataset_format_filter_op_in(self):
        # test pass
        exepression = SimpleExpression(list_value=SimpleExpression.ListValue(string_list=['TABULAR', 'IMAGE']))
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_format_filter_op_in(exepression))
            self.assertTrue('WHERE datasets_v2.dataset_format IN (0, 1)' in self.generate_mysql_statement(query))
        # test raise
        with self.assertRaises(ValueError):
            exepression = SimpleExpression(list_value=SimpleExpression.ListValue(string_list=['FAKE']))
            dataset_format_filter_op_in(exepression)

    def test_dataset_format_filter_op_euqal(self):
        # test pass
        exepression = SimpleExpression(string_value='TABULAR')
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_format_filter_op_equal(exepression))
            self.assertTrue('WHERE datasets_v2.dataset_format = 0' in self.generate_mysql_statement(query))
        # test raise
        with self.assertRaises(ValueError):
            exepression = SimpleExpression(list_value=SimpleExpression.ListValue(string_list=['FAKE']))
            dataset_format_filter_op_equal(exepression)

    def test_dataset_publish_frontend_filter_op_equal(self):
        # test published
        exepression = SimpleExpression(string_value='PUBLISHED')
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_publish_frontend_filter_op_equal(exepression))
            self.assertTrue('WHERE datasets_v2.is_published IS true AND datasets_v2.ticket_status = \'APPROVED\'' in
                            self.generate_mysql_statement(query))

        # test unpublished
        exepression = SimpleExpression(string_value='UNPUBLISHED')
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_publish_frontend_filter_op_equal(exepression))
            self.assertTrue('WHERE datasets_v2.is_published IS false' in self.generate_mysql_statement(query))

        # test ticket_pending
        exepression = SimpleExpression(string_value='TICKET_PENDING')
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_publish_frontend_filter_op_equal(exepression))
            self.assertTrue('WHERE datasets_v2.is_published IS true AND datasets_v2.ticket_status = \'PENDING\'' in
                            self.generate_mysql_statement(query))

        # test ticket declined
        exepression = SimpleExpression(string_value='TICKET_DECLINED')
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_publish_frontend_filter_op_equal(exepression))
            self.assertTrue('WHERE datasets_v2.is_published IS true AND datasets_v2.ticket_status = \'DECLINED\'' in
                            self.generate_mysql_statement(query))

    def test_dataset_auth_status_filter_op_in(self):
        # test authorized
        exepression = SimpleExpression(list_value=SimpleExpression.ListValue(string_list=['AUTHORIZED']))
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_auth_status_filter_op_in(exepression))
            self.assertTrue('WHERE datasets_v2.auth_status IS NULL OR datasets_v2.auth_status IN (\'AUTHORIZED\')' in
                            self.generate_mysql_statement(query))
        # test others
        exepression = SimpleExpression(list_value=SimpleExpression.ListValue(string_list=['PENDING', 'WITHDRAW']))
        with db.session_scope() as session:
            query = session.query(Dataset).filter(dataset_auth_status_filter_op_in(exepression))
            self.assertTrue(
                'WHERE datasets_v2.auth_status IN (\'PENDING\', \'WITHDRAW\')' in self.generate_mysql_statement(query))


if __name__ == '__main__':
    unittest.main()
