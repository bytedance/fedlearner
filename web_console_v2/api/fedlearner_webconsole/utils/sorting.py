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
import re
from typing import NamedTuple, Type, List

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

from fedlearner_webconsole.db import db

_REGEX = re.compile(r'^([a-zA-Z0-9._\-]+)\s(asc|desc)$')


class SortExpression(NamedTuple):
    is_asc: bool
    field: str


def parse_expression(exp: str) -> SortExpression:
    matches = _REGEX.match(exp)
    if not matches:
        error_message = f'[SortExpression] unsupported expression {exp}'
        logging.error(error_message)
        raise ValueError(error_message)
    is_asc = True
    if matches.group(2) == 'desc':
        is_asc = False
    return SortExpression(field=matches.group(1), is_asc=is_asc)


class SorterBuilder(object):

    def __init__(self, model_class: Type[db.Model], supported_fields: List[str]):
        self.model_class = model_class
        for field in supported_fields:
            assert getattr(self.model_class, field, None) is not None, f'{field} is not a column key'
        self.supported_fields = set(supported_fields)

    def build_query(self, query: Query, exp: SortExpression) -> Query:
        if exp.field not in self.supported_fields:
            raise ValueError(f'[SortExpression] unsupported field: {exp.field}')
        column = getattr(self.model_class, exp.field)
        order_fn = asc
        if not exp.is_asc:
            order_fn = desc
        return query.order_by(order_fn(column))
