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

import enum
import logging
from typing import Type, NamedTuple, Dict, Optional, Callable, Any

from pyparsing import Keyword, replace_with, common, dbl_quoted_string, remove_quotes, Suppress, Group, Word, \
    alphas, Literal, Forward, delimited_list, alphanums, Opt, ParseResults, ParseException
from sqlalchemy import Column, and_
from sqlalchemy.orm import Query

from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, SimpleExpression, FilterOp, FilterExpressionKind

# Using pyparsing to construct a DSL for filtering syntax.
# Why not using regex to parse the expression directly? It has a lot of corner cases of handling
# string literally, for example, we use brackets to split sub-expressions, but there may be ')('
# in the value, so we need to try different parsing solution brute-forcefully,  which is inefficient
# and buggy. DSL is a more elegant way. Ref: https://pypi.org/project/pyparsing/
# --------------------Grammar---------------------------
# Names
_SIMPLE_EXP_RNAME = 'simple_exp'
_EXP_COMBINER_RNAME = 'exp_combiner'
_SUB_EXPS_RNAME = 'sub_exps'
_EXP_RNAME = 'exp'
# Those values follow json standards,
# ref: https://github.com/pyparsing/pyparsing/blob/master/examples/jsonParser.py
_LEFT_SQUARE_BRACKET = Suppress('[')
_RIGHT_SQUARE_BRACKET = Suppress(']')
_TRUE = Literal('true').set_parse_action(replace_with(True))
_FALSE = Literal('false').set_parse_action(replace_with(False))
_BOOL_VALUE = _TRUE | _FALSE
_STRING_VALUE = dbl_quoted_string().set_parse_action(remove_quotes)
_NUMBER_VALUE = common.number()
_NUMBER_LIST = Group(_LEFT_SQUARE_BRACKET + Opt(delimited_list(_NUMBER_VALUE, delim=',')) + _RIGHT_SQUARE_BRACKET,
                     aslist=True)
_STRING_LIST = Group(_LEFT_SQUARE_BRACKET + Opt(delimited_list(_STRING_VALUE, delim=',')) + _RIGHT_SQUARE_BRACKET,
                     aslist=True)
PRIMITIVE_VALUE = _BOOL_VALUE | _STRING_VALUE | _NUMBER_VALUE
LIST_VALUE = _NUMBER_LIST | _STRING_LIST
VALUE = PRIMITIVE_VALUE | LIST_VALUE

_LEFT_BRACKET = Suppress('(')
_RIGHT_BRACKET = Suppress(')')
FIELD = Word(init_chars=alphas, body_chars=alphanums + '_' + '.', min=1)
# IN op only support number list value
_IN_EXP_MEMBER = FIELD + Literal(':') + LIST_VALUE
_EQUAL_EXP_MEMBER = FIELD + Literal('=') + PRIMITIVE_VALUE
_GREATER_THAN_EXP_MEMBER = FIELD + Literal('>') + _NUMBER_VALUE
_LESS_THAN_EXP_MEMBER = FIELD + Literal('<') + _NUMBER_VALUE
_CONTAIN_EXP_MEMBER = FIELD + Literal('~=') + _STRING_VALUE
_EXP_MEMBER = _IN_EXP_MEMBER | _EQUAL_EXP_MEMBER | _CONTAIN_EXP_MEMBER | \
              _GREATER_THAN_EXP_MEMBER | _LESS_THAN_EXP_MEMBER
SIMPLE_EXP = Group(_LEFT_BRACKET + _EXP_MEMBER + _RIGHT_BRACKET).set_results_name(_SIMPLE_EXP_RNAME)

EXP_COMBINER = Keyword('and').set_results_name(_EXP_COMBINER_RNAME)
EXP = Forward()
EXP <<= Group(SIMPLE_EXP | (_LEFT_BRACKET + EXP_COMBINER + Group(EXP[2, ...]).set_results_name(_SUB_EXPS_RNAME) +
                            _RIGHT_BRACKET)).set_results_name(_EXP_RNAME)
# --------------------End of grammar--------------------


def _build_simple_expression(parse_results: ParseResults) -> SimpleExpression:
    """Builds simple expression by parsed result, ref to `SIMPLE_EXP`."""
    field, op_str, typed_value = parse_results.as_list()

    op = FilterOp.EQUAL
    if op_str == ':':
        op = FilterOp.IN
    elif op_str == '~=':
        op = FilterOp.CONTAIN
    elif op_str == '>':
        op = FilterOp.GREATER_THAN
    elif op_str == '<':
        op = FilterOp.LESS_THAN
    exp = SimpleExpression(
        field=field,
        op=op,
    )
    if isinstance(typed_value, bool):
        exp.bool_value = typed_value
    elif isinstance(typed_value, str):
        exp.string_value = typed_value
    elif isinstance(typed_value, (int, float)):
        exp.number_value = typed_value
    elif isinstance(typed_value, list):
        if len(typed_value) > 0 and isinstance(typed_value[0], str):
            exp.list_value.string_list.extend(typed_value)
        else:
            exp.list_value.number_list.extend(typed_value)
    else:
        logging.warning('[FilterExpression] Unsupportd value: %s', typed_value)
        raise ValueError(f'Unsupported value: {typed_value}')
    return exp


def _build_expression(exp: ParseResults) -> FilterExpression:
    """Builds expression by parsed results, ref to `EXP`."""
    if _SIMPLE_EXP_RNAME in exp:
        return FilterExpression(kind=FilterExpressionKind.SIMPLE,
                                simple_exp=_build_simple_expression(exp[_SIMPLE_EXP_RNAME]))
    combiner = exp.get(_EXP_COMBINER_RNAME)
    assert combiner == 'and', 'Combiner must be and as of now'
    exp_pb = FilterExpression(kind=FilterExpressionKind.AND)
    for sub_exp in exp.get(_SUB_EXPS_RNAME, []):
        exp_pb.exps.append(_build_expression(sub_exp))
    return exp_pb


def parse_expression(exp: str) -> FilterExpression:
    try:
        parse_results = EXP.parse_string(exp, parse_all=True)
        return _build_expression(parse_results[0])
    except ParseException as e:
        error_message = f'[FilterExpression] unsupported expression {exp}'
        logging.exception(error_message)
        raise ValueError(error_message) from e


class FieldType(enum.Enum):
    STRING = 'STRING'
    NUMBER = 'NUMBER'
    BOOL = 'BOOL'


class SupportedField(NamedTuple):
    # Field type
    type: FieldType
    # Supported ops, key is the op, value is the custom criterion builder.
    ops: Dict['FilterOp', Optional[Callable[[SimpleExpression], Any]]]


def validate_expression(exp: FilterExpression, supported_fields: Dict[str, SupportedField]):
    """Validates if the expression is supported.

    Raises:
        ValueError: if the expression is unsupported.
    """
    if exp.kind == FilterExpressionKind.SIMPLE:
        simple_exp = exp.simple_exp
        if simple_exp.field not in supported_fields:
            raise ValueError(f'Unsupported field {simple_exp.field}')
        supported_field = supported_fields[simple_exp.field]
        if simple_exp.op not in supported_field.ops:
            raise ValueError(f'Unsupported op {FilterOp.Name(simple_exp.op)} on {simple_exp.field}')
        pb_value_field = simple_exp.WhichOneof('value')
        value_type = FieldType.STRING
        if pb_value_field == 'bool_value':
            value_type = FieldType.BOOL
        elif pb_value_field == 'number_value':
            value_type = FieldType.NUMBER
        elif pb_value_field == 'list_value':
            if len(simple_exp.list_value.number_list) > 0:
                value_type = FieldType.NUMBER
            else:
                value_type = FieldType.STRING
        if value_type != supported_field.type:
            raise ValueError(
                f'Type of {simple_exp.field} is invalid, expected {supported_field.type}, actual {value_type}')
        return
    for sub_exp in exp.exps:
        validate_expression(sub_exp, supported_fields)


class FilterBuilder(object):

    def __init__(self, model_class: Type[db.Model], supported_fields: Dict[str, SupportedField]):
        self.model_class = model_class
        self.supported_fields = supported_fields

    def _build_criterions(self, exp: FilterExpression):
        """Builds sqlalchemy criterions for the filter expression."""
        if exp.kind == FilterExpressionKind.SIMPLE:
            simple_exp = exp.simple_exp
            supported_field = self.supported_fields.get(simple_exp.field)
            custom_builder = None
            if supported_field:
                custom_builder = supported_field.ops.get(simple_exp.op)
            # Calls custom builder if it is specified
            if callable(custom_builder):
                return custom_builder(simple_exp)

            column: Optional[Column] = getattr(self.model_class, simple_exp.field, None)
            assert column is not None, f'{simple_exp.field} is not a column key'
            if simple_exp.op == FilterOp.EQUAL:
                pb_value_field = simple_exp.WhichOneof('value')
                return column == getattr(simple_exp, pb_value_field)
            if simple_exp.op == FilterOp.IN:
                number_list = simple_exp.list_value.number_list
                string_list = simple_exp.list_value.string_list
                list_value = number_list
                if len(string_list) > 0:
                    list_value = string_list
                return column.in_(list_value)
            if simple_exp.op == FilterOp.CONTAIN:
                return column.ilike(f'%{simple_exp.string_value}%')
            if simple_exp.op == FilterOp.GREATER_THAN:
                return column > simple_exp.number_value
            if simple_exp.op == FilterOp.LESS_THAN:
                return column < simple_exp.number_value
            raise ValueError(f'Unsupported filter op: {simple_exp.op}')
        # AND-combined sub expressions
        assert exp.kind == FilterExpressionKind.AND
        criterions = [self._build_criterions(sub_exp) for sub_exp in exp.exps]
        return and_(*criterions)

    def build_query(self, query: Query, exp: FilterExpression) -> Query:
        """Build query by expression.

        Raises:
            ValueError: if the expression is unsupported.
        """
        # A special case that the expression is empty
        if exp.ByteSize() == 0:
            return query
        validate_expression(exp, self.supported_fields)
        return query.filter(self._build_criterions(exp))
