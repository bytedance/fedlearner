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
from typing import Any

from pyparsing import ParseException, ParserElement
from sqlalchemy import and_

from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, SimpleExpression, FilterOp, FilterExpressionKind
from fedlearner_webconsole.utils.filtering import VALUE, SIMPLE_EXP, EXP, parse_expression, FilterBuilder, \
    SupportedField, FieldType, validate_expression
from testing.no_web_server_test_case import NoWebServerTestCase


class TestModel(db.Model):
    __tablename__ = 'test_table'
    __table_args__ = (default_table_args('Test table'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))
    disabled = db.Column(db.Boolean, default=False)
    amount = db.Column(db.Float, default=0)


class DslTest(unittest.TestCase):

    def _parse_single(self, e: ParserElement, s: str) -> Any:
        results = e.parse_string(s, parse_all=True).as_list()
        self.assertEqual(len(results), 1)
        return results[0]

    def test_bool_value(self):
        self.assertEqual(self._parse_single(VALUE, 'true'), True)
        self.assertEqual(self._parse_single(VALUE, ' false '), False)
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, 'True')

    def test_string_value(self):
        self.assertEqual(self._parse_single(VALUE, '"u你好🤩 ok"'), 'u你好🤩 ok')
        self.assertEqual(self._parse_single(VALUE, '"hey"'), 'hey')
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, '\'single quote\'')
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, '"no quote pair')
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, 'no quote')

    def test_number_value(self):
        self.assertEqual(self._parse_single(VALUE, '01234'), 1234)
        self.assertEqual(self._parse_single(VALUE, '-56.877'), -56.877)
        self.assertEqual(self._parse_single(VALUE, '1e4'), 10000)
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, '2^20')

    def test_number_list(self):
        self.assertEqual(self._parse_single(VALUE, '[]'), [])
        self.assertEqual(self._parse_single(VALUE, '[-2e2]'), [-200])
        self.assertEqual(self._parse_single(VALUE, '[-1, +2.06,  3]'), [-1, 2.06, 3])
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, '-2 ]')

    def test_string_list(self):
        self.assertEqual(self._parse_single(VALUE, '["hello world"]'), ['hello world'])
        self.assertEqual(self._parse_single(VALUE, '["🐷", "行\\\"卫\'qiang", "🤩"]'), ['🐷', '行\\"卫\'qiang', '🤩'])
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, '[\'hello\']')
        with self.assertRaises(ParseException):
            self._parse_single(VALUE, '["hello]')

    def test_simple_exp_with_equal(self):
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(abc=123)'), ['abc', '=', 123])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(a_b_c=false)'), ['a_b_c', '=', False])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(x123="test值")'), ['x123', '=', 'test值'])
        with self.assertRaises(ParseException):
            # Without brackets
            self._parse_single(SIMPLE_EXP, 'abc=123')
        with self.assertRaises(ParseException):
            # Invalid value
            self._parse_single(SIMPLE_EXP, 'abc=abc')
        with self.assertRaises(ParseException):
            # List value is not supported for equal
            self._parse_single(SIMPLE_EXP, '(f=[1,-2])')

    def test_simple_exp_with_in(self):
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(abc:[1,-2])'), ['abc', ':', [1, -2]])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(x12_3:[2.3333])'), ['x12_3', ':', [2.3333]])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(s1:["h","w"])'), ['s1', ':', ['h', 'w']])
        with self.assertRaises(ParseException):
            # Without brackets
            self._parse_single(SIMPLE_EXP, 'abc:[-1]')
        with self.assertRaises(ParseException):
            # Primitive value is not supported
            self._parse_single(SIMPLE_EXP, '(f:"hello")')

    def test_simple_exp_with_greater_than(self):
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(start_at>123)'), ['start_at', '>', 123])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(amount>-1.2)'), ['amount', '>', -1.2])
        with self.assertRaises(ParseException):
            # String value is not supported
            self._parse_single(SIMPLE_EXP, '(s>"hello")')

    def test_simple_exp_with_less_than(self):
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(end_at<187777)'), ['end_at', '<', 187777])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(amount <  -1.23)'), ['amount', '<', -1.23])
        with self.assertRaises(ParseException):
            # String value is not supported
            self._parse_single(SIMPLE_EXP, '(amount<"hello")')

    def test_simple_exp_with_contain(self):
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(abc~="keyword")'), ['abc', '~=', 'keyword'])
        self.assertEqual(self._parse_single(SIMPLE_EXP, '(a_b_c~="~=你好")'), ['a_b_c', '~=', '~=你好'])
        with self.assertRaises(ParseException):
            # Without brackets
            self._parse_single(SIMPLE_EXP, 'abc~="keyword"')
        with self.assertRaises(ParseException):
            # Invalid value
            self._parse_single(SIMPLE_EXP, 'abc~=abc')
        with self.assertRaises(ParseException):
            # List value is not supported
            self._parse_single(SIMPLE_EXP, '(f~=["fff"])')

    def test_exp_simple(self):
        self.assertEqual(self._parse_single(EXP, '(a.b:[1,2,3])'), [['a.b', ':', [1, 2, 3]]])
        self.assertEqual(self._parse_single(EXP, '(x123="h h")'), [['x123', '=', 'h h']])
        self.assertEqual(self._parse_single(EXP, '(s1~="ooo")'), [['s1', '~=', 'ooo']])

    def test_exp_and_combined(self):
        result = self._parse_single(EXP, '(and(a:[1])(b=true)(c=")(")(d~="like"))')
        self.assertEqual(result,
                         ['and', [[['a', ':', [1]]], [['b', '=', True]], [['c', '=', ')(']], [['d', '~=', 'like']]]])
        with self.assertRaises(ParseException):
            # No brackets
            self._parse_single(EXP, 'and(f=false)(x=true)')
        with self.assertRaises(ParseException):
            # Only one sub-exp
            self._parse_single(EXP, '(and(f=false))')
        with self.assertRaises(ParseException):
            # Invalid value
            self._parse_single(EXP, '(and(f=false)(x=)())')

    def test_exp_nested(self):
        result = self._parse_single(EXP, '(and(a:[1,2])(and(x1=true)(x2=false)(x3~="ss"))(and(y1="and()")(y2="中文")))')
        self.assertEqual(result, [
            'and',
            [[['a', ':', [1, 2]]], ['and', [[['x1', '=', True]], [['x2', '=', False]], [['x3', '~=', 'ss']]]],
             ['and', [[['y1', '=', 'and()']], [['y2', '=', '中文']]]]]
        ])


class ParseExpressionTest(unittest.TestCase):

    def test_simple_expression(self):
        self.assertEqual(
            parse_expression('(test_field="hey 🐷")'),
            FilterExpression(kind=FilterExpressionKind.SIMPLE,
                             simple_exp=SimpleExpression(field='test_field', op=FilterOp.EQUAL, string_value='hey 🐷')))
        self.assertEqual(
            parse_expression('(test_field:[ -2, 3    ])'),
            FilterExpression(kind=FilterExpressionKind.SIMPLE,
                             simple_exp=SimpleExpression(field='test_field',
                                                         op=FilterOp.IN,
                                                         list_value=SimpleExpression.ListValue(number_list=[-2, 3]))))
        self.assertEqual(
            parse_expression('(test_field:["你    好", "🐷"])'),
            FilterExpression(kind=FilterExpressionKind.SIMPLE,
                             simple_exp=SimpleExpression(
                                 field='test_field',
                                 op=FilterOp.IN,
                                 list_value=SimpleExpression.ListValue(string_list=['你    好', '🐷']))))
        self.assertEqual(
            parse_expression('(test_field~="like")'),
            FilterExpression(kind=FilterExpressionKind.SIMPLE,
                             simple_exp=SimpleExpression(field='test_field', op=FilterOp.CONTAIN, string_value='like')))
        self.assertEqual(
            parse_expression('(start_at > 123)'),
            FilterExpression(kind=FilterExpressionKind.SIMPLE,
                             simple_exp=SimpleExpression(field='start_at', op=FilterOp.GREATER_THAN, number_value=123)))
        self.assertEqual(
            parse_expression('(test_field<-12.3)'),
            FilterExpression(kind=FilterExpressionKind.SIMPLE,
                             simple_exp=SimpleExpression(field='test_field', op=FilterOp.LESS_THAN,
                                                         number_value=-12.3)))

    def test_and_expression(self):
        self.assertEqual(
            parse_expression('(and(x1="床前明月光")(x2:["o","y"])(x3=true))'),
            FilterExpression(kind=FilterExpressionKind.AND,
                             exps=[
                                 FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                  simple_exp=SimpleExpression(field='x1',
                                                                              op=FilterOp.EQUAL,
                                                                              string_value='床前明月光')),
                                 FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                  simple_exp=SimpleExpression(
                                                      field='x2',
                                                      op=FilterOp.IN,
                                                      list_value=SimpleExpression.ListValue(string_list=['o', 'y']))),
                                 FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                  simple_exp=SimpleExpression(field='x3',
                                                                              op=FilterOp.EQUAL,
                                                                              bool_value=True))
                             ]))

    def test_nested_expression(self):
        self.assertEqual(
            parse_expression('(and(and(x1="(and(x1=true)(x2=false))")(x2:[1]))(and(x3=false)(x4=1.1e3))(x5~="x"))'),
            FilterExpression(kind=FilterExpressionKind.AND,
                             exps=[
                                 FilterExpression(kind=FilterExpressionKind.AND,
                                                  exps=[
                                                      FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                                       simple_exp=SimpleExpression(
                                                                           field='x1',
                                                                           op=FilterOp.EQUAL,
                                                                           string_value='(and(x1=true)(x2=false))')),
                                                      FilterExpression(
                                                          kind=FilterExpressionKind.SIMPLE,
                                                          simple_exp=SimpleExpression(
                                                              field='x2',
                                                              op=FilterOp.IN,
                                                              list_value=SimpleExpression.ListValue(number_list=[1]))),
                                                  ]),
                                 FilterExpression(kind=FilterExpressionKind.AND,
                                                  exps=[
                                                      FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                                       simple_exp=SimpleExpression(field='x3',
                                                                                                   op=FilterOp.EQUAL,
                                                                                                   bool_value=False)),
                                                      FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                                       simple_exp=SimpleExpression(field='x4',
                                                                                                   op=FilterOp.EQUAL,
                                                                                                   number_value=1100)),
                                                  ]),
                                 FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                  simple_exp=SimpleExpression(field='x5',
                                                                              op=FilterOp.CONTAIN,
                                                                              string_value='x')),
                             ]))

    def test_invalid_expression(self):
        with self.assertRaises(ValueError):
            # No brackets
            parse_expression('x1=true')
        with self.assertRaises(ValueError):
            # No brackets
            parse_expression('and(x1=true)(x2=false)')
        with self.assertRaises(ValueError):
            # Only one sub expression
            parse_expression('(and(x1=true))')


class ValidateExpressionTest(unittest.TestCase):
    SUPPORTED_FIELDS = {
        'f1': SupportedField(type=FieldType.NUMBER, ops={FilterOp.IN: None}),
        'f2': SupportedField(type=FieldType.STRING, ops={
            FilterOp.EQUAL: lambda exp: True,
            FilterOp.IN: None
        }),
        'f3': SupportedField(type=FieldType.BOOL, ops={FilterOp.EQUAL: None}),
        'f4': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
    }

    def test_valid(self):
        exp = FilterExpression(kind=FilterExpressionKind.AND,
                               exps=[
                                   FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                    simple_exp=SimpleExpression(
                                                        field='f1',
                                                        op=FilterOp.IN,
                                                        list_value=SimpleExpression.ListValue(number_list=[1, 2]))),
                                   FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                    simple_exp=SimpleExpression(
                                                        field='f2',
                                                        op=FilterOp.IN,
                                                        list_value=SimpleExpression.ListValue(string_list=['hello']))),
                                   FilterExpression(kind=FilterExpressionKind.AND,
                                                    exps=[
                                                        FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                                         simple_exp=SimpleExpression(
                                                                             field='f2',
                                                                             op=FilterOp.EQUAL,
                                                                             string_value='hello')),
                                                        FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                                         simple_exp=SimpleExpression(field='f3',
                                                                                                     op=FilterOp.EQUAL,
                                                                                                     bool_value=True)),
                                                    ]),
                                   FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                    simple_exp=SimpleExpression(field='f4',
                                                                                op=FilterOp.CONTAIN,
                                                                                string_value='lifjfasdf asdf')),
                               ])
        validate_expression(exp, self.SUPPORTED_FIELDS)

    def test_unsupported_field(self):
        exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                               simple_exp=SimpleExpression(field='f123123',
                                                           op=FilterOp.IN,
                                                           list_value=SimpleExpression.ListValue(number_list=[1, 2])))
        with self.assertRaisesRegex(ValueError, 'Unsupported field f123123'):
            validate_expression(exp, self.SUPPORTED_FIELDS)

    def test_unsupported_op(self):
        exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                               simple_exp=SimpleExpression(field='f3',
                                                           op=FilterOp.IN,
                                                           list_value=SimpleExpression.ListValue(number_list=[1, 2])))
        with self.assertRaisesRegex(ValueError, 'Unsupported op IN on f3'):
            validate_expression(exp, self.SUPPORTED_FIELDS)

    def test_invalid_type(self):
        exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                               simple_exp=SimpleExpression(field='f1', op=FilterOp.IN, string_value='invalid'))
        with self.assertRaisesRegex(ValueError,
                                    'Type of f1 is invalid, expected FieldType.NUMBER, actual FieldType.STRING'):
            validate_expression(exp, self.SUPPORTED_FIELDS)
        exp = FilterExpression(kind=FilterExpressionKind.SIMPLE,
                               simple_exp=SimpleExpression(field='f2',
                                                           op=FilterOp.IN,
                                                           list_value=SimpleExpression.ListValue(number_list=[1])))
        with self.assertRaisesRegex(ValueError,
                                    'Type of f2 is invalid, expected FieldType.STRING, actual FieldType.NUMBER'):
            validate_expression(exp, self.SUPPORTED_FIELDS)


class FilterBuilderTest(NoWebServerTestCase):

    def test_build_query(self):
        exp = FilterExpression(kind=FilterExpressionKind.AND,
                               exps=[
                                   FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                    simple_exp=SimpleExpression(
                                                        field='id',
                                                        op=FilterOp.IN,
                                                        list_value=SimpleExpression.ListValue(number_list=[1, 2]))),
                                   FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                    simple_exp=SimpleExpression(field='name',
                                                                                op=FilterOp.EQUAL,
                                                                                string_value='test name')),
                                   FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                    simple_exp=SimpleExpression(field='name',
                                                                                op=FilterOp.CONTAIN,
                                                                                string_value='test')),
                                   FilterExpression(
                                       kind=FilterExpressionKind.AND,
                                       exps=[
                                           FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                            simple_exp=SimpleExpression(field='disabled',
                                                                                        op=FilterOp.EQUAL,
                                                                                        bool_value=True)),
                                           FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                            simple_exp=SimpleExpression(field='amount',
                                                                                        op=FilterOp.EQUAL,
                                                                                        number_value=666.6)),
                                           FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                            simple_exp=SimpleExpression(field='id',
                                                                                        op=FilterOp.GREATER_THAN,
                                                                                        number_value=1)),
                                           FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                                            simple_exp=SimpleExpression(field='id',
                                                                                        op=FilterOp.LESS_THAN,
                                                                                        number_value=1999)),
                                       ]),
                               ])
        with db.session_scope() as session:
            models = [
                TestModel(
                    id=1,
                    name='test name',
                    disabled=False,
                    amount=666.6,
                ),
                TestModel(
                    id=2,
                    name='test name',
                    disabled=True,
                    amount=666.6,
                ),
                TestModel(
                    id=3,
                    name='test name',
                    disabled=True,
                    amount=666.6,
                )
            ]
            session.add_all(models)
            session.commit()

        def amount_filter(exp: FilterExpression):
            return and_(TestModel.amount > 600, TestModel.amount < 700)

        builder = FilterBuilder(TestModel,
                                supported_fields={
                                    'id':
                                        SupportedField(type=FieldType.NUMBER,
                                                       ops={
                                                           FilterOp.EQUAL: None,
                                                           FilterOp.IN: None,
                                                           FilterOp.GREATER_THAN: None,
                                                           FilterOp.LESS_THAN: None,
                                                       }),
                                    'name':
                                        SupportedField(type=FieldType.STRING,
                                                       ops={
                                                           FilterOp.EQUAL: None,
                                                           FilterOp.CONTAIN: None
                                                       }),
                                    'disabled':
                                        SupportedField(type=FieldType.BOOL, ops={FilterOp.EQUAL: None}),
                                    'amount':
                                        SupportedField(type=FieldType.NUMBER, ops={FilterOp.EQUAL: amount_filter}),
                                })
        with db.session_scope() as session:
            query = session.query(TestModel)
            query = builder.build_query(query, exp)
            self.assertEqual(
                self.generate_mysql_statement(query),
                'SELECT test_table.id, test_table.name, test_table.disabled, test_table.amount \n'
                'FROM test_table \n'
                # lower() is called since it is meant to be case-insensitive
                # pylint: disable-next=line-too-long
                'WHERE test_table.id IN (1.0, 2.0) AND test_table.name = \'test name\' AND lower(test_table.name) LIKE lower(\'%%test%%\') AND test_table.disabled = true AND test_table.amount > 600 AND test_table.amount < 700 AND test_table.id > 1.0 AND test_table.id < 1999.0'
            )
            model_ids = [m.id for m in query.all()]
            self.assertCountEqual(model_ids, [2])

    def test_build_query_for_empty_exp(self):
        exp = FilterExpression()
        builder = FilterBuilder(TestModel, supported_fields={})
        with db.session_scope() as session:
            query = session.query(TestModel)
            query = builder.build_query(query, exp)
            self.assertEqual(
                self.generate_mysql_statement(query),
                'SELECT test_table.id, test_table.name, test_table.disabled, test_table.amount \n'
                'FROM test_table')


if __name__ == '__main__':
    unittest.main()
