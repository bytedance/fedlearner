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
from unittest.mock import patch

from envs import _SQLALCHEMY_DATABASE_URI_PATTERN, Envs


class EnvsTest(unittest.TestCase):

    def test_sqlalchemy_database_uri_pattern(self):
        # Sqlite
        matches = _SQLALCHEMY_DATABASE_URI_PATTERN.match('sqlite:///app.db')
        self.assertIsNotNone(matches)
        self.assertEqual(matches.group('dialect'), 'sqlite')
        self.assertIsNone(matches.group('driver'))
        self.assertIsNone(matches.group('username'))
        self.assertIsNone(matches.group('password'))
        self.assertIsNone(matches.group('host'))
        self.assertIsNone(matches.group('port'))
        self.assertEqual(matches.group('database'), 'app.db')
        # MySQL
        matches = _SQLALCHEMY_DATABASE_URI_PATTERN.match('mysql+pymysql://root:root@localhost:33600/fedlearner')
        self.assertIsNotNone(matches)
        self.assertEqual(matches.group('dialect'), 'mysql')
        self.assertEqual(matches.group('driver'), 'pymysql')
        self.assertEqual(matches.group('username'), 'root')
        self.assertEqual(matches.group('password'), 'root')
        self.assertEqual(matches.group('host'), 'localhost')
        self.assertEqual(matches.group('port'), '33600')
        self.assertEqual(matches.group('database'), 'fedlearner')
        # MySQL with socket
        matches = _SQLALCHEMY_DATABASE_URI_PATTERN.match('mysql+pymysql://:@/?charset=utf8mb4db_psm=mysql.fedlearner')
        self.assertIsNotNone(matches)
        self.assertEqual(matches.group('dialect'), 'mysql')
        self.assertEqual(matches.group('driver'), 'pymysql')
        self.assertIsNone(matches.group('username'))
        self.assertIsNone(matches.group('password'))
        self.assertIsNone(matches.group('host'))
        self.assertIsNone(matches.group('port'))
        self.assertIsNone(matches.group('database'))
        # Invalid ones
        matches = _SQLALCHEMY_DATABASE_URI_PATTERN.match('mysql+pymysql://root_33600/fedlearner')
        self.assertIsNone(matches)
        matches = _SQLALCHEMY_DATABASE_URI_PATTERN.match('sqlite://hello')
        self.assertIsNone(matches)

    def test_check_db_envs_valid(self):
        with patch('envs.Envs.SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://root:proot@localhost:33600/fedlearner'), \
                patch('envs.Envs.DB_HOST', 'localhost'), \
                patch('envs.Envs.DB_PORT', '33600'), \
                patch('envs.Envs.DB_DATABASE', 'fedlearner'), \
                patch('envs.Envs.DB_USERNAME', 'root'), \
                patch('envs.Envs.DB_PASSWORD', 'proot'):
            self.assertIsNone(Envs._check_db_envs())  # pylint: disable=protected-access
        # DB_HOST is not set
        with patch('envs.Envs.SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://:@/?charset=utf8mb4db_psm=mysql.fedlearner'):
            self.assertIsNone(Envs._check_db_envs())  # pylint: disable=protected-access
        # DB_PASSWORD with some encodings
        with patch('envs.Envs.SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://root:fl%4012345@localhost:33600/fedlearner'), \
                patch('envs.Envs.DB_HOST', 'localhost'), \
                patch('envs.Envs.DB_PORT', '33600'), \
                patch('envs.Envs.DB_DATABASE', 'fedlearner'), \
                patch('envs.Envs.DB_USERNAME', 'root'), \
                patch('envs.Envs.DB_PASSWORD', 'fl@12345'):
            self.assertIsNone(Envs._check_db_envs())  # pylint: disable=protected-access

    def test_check_db_envs_invalid(self):
        with patch('envs.Envs.SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://root:proot@localhost:33600/fedlearner'), \
                patch('envs.Envs.DB_HOST', 'localhost'), \
                patch('envs.Envs.DB_PORT', '336'):
            self.assertEqual(Envs._check_db_envs(), 'DB_PORT does not match')  # pylint: disable=protected-access
        with patch('envs.Envs.SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://:@/?charset=utf8mb4db_psm=mysql.fedlearner'), \
                patch('envs.Envs.DB_HOST', 'localhost'):
            self.assertEqual(Envs._check_db_envs(), 'DB_HOST does not match')  # pylint: disable=protected-access

    def test_decode_url_codec(self):
        self.assertIsNone(Envs._decode_url_codec(None))  # pylint: disable=protected-access
        self.assertEqual(Envs._decode_url_codec('hahaha'), 'hahaha')  # pylint: disable=protected-access
        self.assertEqual(Envs._decode_url_codec('%20%40'), ' @')  # pylint: disable=protected-access

    def test_system_info_valid(self):
        with patch('envs.Envs.SYSTEM_INFO', '{"domain_name": "aaa.fedlearner.net", "name": "aaa.Inc"}'):
            self.assertIsNone(Envs._check_system_info_envs())  # pylint: disable=protected-access

    def test_system_info_invalid(self):
        with patch('envs.Envs.SYSTEM_INFO', '{"domain_name": "aaa.fedlearner.net"}'):
            self.assertEqual('domain_name or name is not set into SYSTEM_INFO', Envs._check_system_info_envs())  # pylint: disable=protected-access

        with patch('envs.Envs.SYSTEM_INFO', '{"domain_name": "aaa.fedlearner.net"'):
            self.assertIn('failed to parse SYSTEM_INFO', Envs._check_system_info_envs())  # pylint: disable=protected-access


if __name__ == '__main__':
    unittest.main()
