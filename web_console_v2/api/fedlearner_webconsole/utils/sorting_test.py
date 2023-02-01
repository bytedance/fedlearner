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

from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.utils.sorting import parse_expression, SortExpression, SorterBuilder
from testing.no_web_server_test_case import NoWebServerTestCase


class ParseExpressionTest(unittest.TestCase):

    def test_invalid_exp(self):
        # No space
        with self.assertRaises(ValueError):
            parse_expression('fieldasc')
        # Invalid field name
        with self.assertRaises(ValueError):
            parse_expression('field你 asc')
        # Invalid asc sign
        with self.assertRaises(ValueError):
            parse_expression('fiele dasc')

    def test_valid_exp(self):
        self.assertEqual(parse_expression('ff_GG-1 asc'), SortExpression(field='ff_GG-1', is_asc=True))
        self.assertEqual(parse_expression('f.a.b desc'), SortExpression(field='f.a.b', is_asc=False))


class TestModel(db.Model):
    __tablename__ = 'test_table'
    __table_args__ = (default_table_args('Test table'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    amount = db.Column(db.Float, default=0)


class SorterBuilderTest(NoWebServerTestCase):

    def test_supported_field(self):
        with self.assertRaises(AssertionError):
            SorterBuilder(model_class=TestModel, supported_fields=['id', 'amount', 'non-existing'])

    def test_build_query(self):
        self.maxDiff = None
        builder = SorterBuilder(model_class=TestModel, supported_fields=['id', 'amount'])
        with db.session_scope() as session:
            query = session.query(TestModel)
            # Invalid one
            sort_exp = SortExpression(field='f1', is_asc=True)
            with self.assertRaisesRegex(ValueError, 'unsupported field: f1'):
                builder.build_query(query, sort_exp)
            # Valid ones
            sort_exp = SortExpression(field='id', is_asc=True)
            statement = self.generate_mysql_statement(builder.build_query(query, sort_exp))
            self.assertEqual(statement, 'SELECT test_table.id, test_table.amount \n'
                             'FROM test_table ORDER BY test_table.id ASC')
            sort_exp = SortExpression(field='amount', is_asc=False)
            statement = self.generate_mysql_statement(builder.build_query(query, sort_exp))
            self.assertEqual(
                statement, 'SELECT test_table.id, test_table.amount \n'
                'FROM test_table ORDER BY test_table.amount DESC')


if __name__ == '__main__':
    unittest.main()
