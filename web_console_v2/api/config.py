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


class Config(object):
    SQLALCHEMY_DATABASE_URI = \
        '{}?init_command=SET SESSION time_zone=\'%2B00:00\''.format(
            os.getenv(
                'SQLALCHEMY_DATABASE_URI',
                'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
            ))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MYSQL_CHARSET = 'utf8mb4'
    # For unicode strings
    # Ref: https://stackoverflow.com/questions/14853694/python-jsonify-dictionary-in-utf-8
    JSON_AS_ASCII = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY',
                               secrets.token_urlsafe(64))
    PROPAGATE_EXCEPTIONS = True
    LOGGING_LEVEL = logging.INFO
    GRPC_LISTEN_PORT = 1990
    JWT_ACCESS_TOKEN_EXPIRES = 86400
    ES_HOST = 'fedlearner-stack-elasticsearch-client'
    ES_PORT = 9200
    STORAGE_ROOT = os.getenv('STORAGE_ROOT', '/data')

    START_GRPC_SERVER = True
    START_SCHEDULER = True
