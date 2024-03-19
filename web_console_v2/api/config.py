# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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

from fedlearner_webconsole.db import get_database_uri
from envs import Envs


class Config(object):
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MYSQL_CHARSET = 'utf8mb4'
    # For unicode strings
    # Ref: https://stackoverflow.com/questions/14853694/python-jsonify-dictionary-in-utf-8
    JSON_AS_ASCII = False
    JWT_SECRET_KEY = Envs.JWT_SECRET_KEY
    PROPAGATE_EXCEPTIONS = True
    GRPC_LISTEN_PORT = Envs.GRPC_LISTEN_PORT
    JWT_ACCESS_TOKEN_EXPIRES = 86400
    STORAGE_ROOT = Envs.STORAGE_ROOT

    START_SCHEDULER = True
    START_K8S_WATCHER = True
