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
# pylint: disable=wrong-import-position, global-statement, cyclic-import

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restful import Api
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
api = Api(prefix='/api/v2')
jwt = JWTManager()
current_app = None

from fedlearner_webconsole.auth.apis import initialize_auth_apis
from fedlearner_webconsole.rpc.server import RPCServer

rpc_server = RPCServer()


def create_app(config):
    global current_app
    app = Flask('fedlearner_webconsole')
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    initialize_auth_apis(api)
    api.init_app(app)

    rpc_server.stop()
    rpc_server.start(1990)

    current_app = app
    return app
