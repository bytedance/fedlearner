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

import os
import unittest
from typing import Dict, Any, List, Optional, Union

from itertools import zip_longest
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Query

from envs import Envs
from fedlearner_webconsole.db import db, turn_db_timezone_to_utc
from uuid import uuid4


def create_all_tables(database_uri: str = None):
    if database_uri:
        db.rebind(database_uri)

    # If there's a db file due to some reason, remove it first.
    if db.metadata.tables.values():
        db.drop_all()
    db.create_all()


class NoWebServerTestCase(unittest.TestCase):
    """A base test case class which does not depend on API server.
    """

    class Config(object):
        SQLALCHEMY_DATABASE_URI = \
            f'sqlite:///{os.path.join(Envs.BASE_DIR, f"{uuid4()}-app.db?check_same_thread=False")}'

    def setUp(self) -> None:
        super().setUp()
        create_all_tables(turn_db_timezone_to_utc(self.__class__.Config.SQLALCHEMY_DATABASE_URI))

    def tearDown(self) -> None:
        db.drop_all()
        return super().tearDown()

    @classmethod
    def generate_mysql_statement(cls, query: Query) -> str:
        # Uses mysql dialect for testing, and `literal_binds` to inline the parameters.
        return str(query.statement.compile(dialect=mysql.dialect(), compile_kwargs={'literal_binds': True}))

    def assertDictPartiallyEqual(self,
                                 actual_dict: Dict[Any, Any],
                                 expected_dict: Dict[Any, Any],
                                 ignore_fields: Optional[List[Any]] = None):
        """Asserts if the data in dict equals to expected_data.
           we ignore ignore_fields in dict.
        """
        if ignore_fields is None:
            ignore_fields = []
        # Shallow copy
        actual_dict = actual_dict.copy()
        expected_dict = expected_dict.copy()
        for field in ignore_fields:
            if field in actual_dict.keys():
                del actual_dict[field]
            if field in expected_dict.keys():
                del expected_dict[field]

        self.assertDictEqual(actual_dict, expected_dict)

    def assertPartiallyEqual(self,
                             actual_data: Union[Dict, List],
                             expected_data: Union[Dict, List],
                             ignore_fields: Optional[List] = None):
        if isinstance(actual_data, list):
            for a, e in zip_longest(actual_data, expected_data, fillvalue={}):
                self.assertDictPartiallyEqual(a, e, ignore_fields)
            return
        self.assertDictPartiallyEqual(actual_data, expected_data, ignore_fields)
