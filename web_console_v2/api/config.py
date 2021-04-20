# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import logging
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def turn_db_timezone_to_utc(original_uri: str) -> str:
    """ string operator that make any db into utc timezone

    Args:
        original_uri (str): original uri without set timezone

    Returns:
        str: uri with explicittly set utc timezone
    """
    # Do set use `init_command` for sqlite, since it doesn't support yet
    if original_uri.startswith('sqlite'):
        return original_uri

    _set_timezone_args = 'init_command=SET SESSION time_zone=\'%2B00:00\''
    parsed_uri = original_uri.split('?')

    if len(parsed_uri) == 1:
        return f'{parsed_uri[0]}?{_set_timezone_args}'
    assert len(
        parsed_uri
    ) == 2, f'failed to parse uri [{original_uri}], since it has more than one ?'

    base_uri, args = parsed_uri
    args = args.split('&&')
    # remove if there's init_command already
    args_list = [_set_timezone_args]
    for a in args:
        if a.startswith('init_command'):
            command = a.split('=')[1]
            # ignore other set time_zone args
            if command.startswith('SET SESSION time_zone'):
                continue
            args_list[0] = f'{args_list[0]};{command}'
        else:
            args_list.append(a)

    args = '&&'.join(args_list)
    return f'{base_uri}?{args}'


class Config(object):
    SQLALCHEMY_DATABASE_URI = turn_db_timezone_to_utc(
        os.getenv('SQLALCHEMY_DATABASE_URI',
                  'sqlite:///' + os.path.join(BASE_DIR, 'app.db')))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MYSQL_CHARSET = 'utf8mb4'
    # For unicode strings
    # Ref: https://stackoverflow.com/questions/14853694/python-jsonify-dictionary-in-utf-8
    JSON_AS_ASCII = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(64))
    PROPAGATE_EXCEPTIONS = True
    LOGGING_LEVEL = logging.INFO
    GRPC_LISTEN_PORT = 1990
    JWT_ACCESS_TOKEN_EXPIRES = 86400
    STORAGE_ROOT = os.getenv('STORAGE_ROOT', '/data')

    START_GRPC_SERVER = True
    START_SCHEDULER = True
    START_COMPOSER = os.getenv('START_COMPOSER', True)
