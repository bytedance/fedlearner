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
import logging

from envs import Envs
from fedlearner_webconsole.app import create_app
from tools.local_runner.initial_db import init_db

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app_a.db')
    MYSQL_CHARSET = 'utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    JWT_SECRET_KEY = 'secret'
    PROPAGATE_EXCEPTIONS = True
    LOGGING_LEVEL = logging.INFO
    GRPC_LISTEN_PORT = 1993
    JWT_ACCESS_TOKEN_EXPIRES = 86400
    STORAGE_ROOT = Envs.STORAGE_ROOT

    START_GRPC_SERVER = True
    START_SCHEDULER = True
    START_COMPOSER = True


app = create_app(Config)


@app.cli.command('create-db')
def create_db():
    init_db(1991, 'fl-demo2.com')
