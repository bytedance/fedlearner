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
from config import Config
from fedlearner_webconsole.app import create_app
from fedlearner_webconsole.db import db_handler as db
from fedlearner_webconsole.initial_db import initial_db
from flask_migrate import Migrate

from fedlearner_webconsole.utils.hooks import pre_start_hook


class CliConfig(Config):
    START_GRPC_SERVER = False
    START_SCHEDULER = False
    START_COMPOSER = False


pre_start_hook()
migrate = Migrate()
app = create_app(CliConfig())
migrate.init_app(app, db)


@app.cli.command('create-initial-data')
def create_initial_data():
    initial_db()


@app.cli.command('create-db')
def create_db():
    db.create_all()
