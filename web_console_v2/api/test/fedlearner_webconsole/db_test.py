# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import os
import unittest

from fedlearner_webconsole.db import get_database_uri, _turn_db_timezone_to_utc
from fedlearner_webconsole.proto import common_pb2


class EngineSessionTest(unittest.TestCase):
    def test_turn_db_timezone_to_utc(self):
        sqlite_uri = 'sqlite:///app.db'
        self.assertEqual(_turn_db_timezone_to_utc(sqlite_uri),
                         'sqlite:///app.db')

        mysql_uri_naive = 'mysql+pymysql://root:root@localhost:33600/fedlearner'
        self.assertEqual(
            _turn_db_timezone_to_utc(mysql_uri_naive),
            'mysql+pymysql://root:root@localhost:33600/fedlearner?init_command=SET SESSION time_zone=\'%2B00:00\''
        )

        mysql_uri_with_init_command = 'mysql+pymysql://root:root@localhost:33600/fedlearner?init_command=HELLO'
        self.assertEqual(
            _turn_db_timezone_to_utc(mysql_uri_with_init_command),
            'mysql+pymysql://root:root@localhost:33600/fedlearner?init_command=SET SESSION time_zone=\'%2B00:00\';HELLO'
        )

        mysql_uri_with_other_args = 'mysql+pymysql://root:root@localhost:33600/fedlearner?charset=utf8mb4'
        self.assertEqual(
            _turn_db_timezone_to_utc(mysql_uri_with_other_args),
            'mysql+pymysql://root:root@localhost:33600/fedlearner?init_command=SET SESSION time_zone=\'%2B00:00\'&&charset=utf8mb4'
        )

        mysql_uri_with_set_time_zone = 'mysql+pymysql://root:root@localhost:33600/fedlearner?init_command=SET SESSION time_zone=\'%2B08:00\''
        self.assertEqual(
            _turn_db_timezone_to_utc(mysql_uri_with_set_time_zone),
            'mysql+pymysql://root:root@localhost:33600/fedlearner?init_command=SET SESSION time_zone=\'%2B00:00\''
        )

    def test_get_database_uri(self):
        # test with environmental variable
        os.environ[
            'SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:33600/fedlearner'
        self.assertTrue(get_database_uri().startswith(
            'mysql+pymysql://root:root@localhost:33600/fedlearner'))

        # test with fallback options
        os.environ.pop('SQLALCHEMY_DATABASE_URI')
        self.assertTrue(get_database_uri().startswith('sqlite:///'))


if __name__ == '__main__':
    unittest.main()
