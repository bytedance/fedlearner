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
import click

from config import Config
from flask_migrate import Migrate
from es_configuration import es_config
from fedlearner_webconsole.app import create_app
from fedlearner_webconsole.db import db
from fedlearner_webconsole.initial_db import initial_db
from fedlearner_webconsole.utils.hooks import pre_start_hook
from tools.project_cleanup import delete_project
from tools.workflow_migration.workflow_completed_failed import migrate_workflow_completed_failed_state
from tools.dataset_migration.dataset_job_name_migration.dataset_job_name_migration import migrate_dataset_job_name
from tools.variable_finder import find


class CliConfig(Config):
    START_SCHEDULER = False
    START_K8S_WATCHER = False


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


@app.cli.command('cleanup-project')
@click.argument('project_id')
def cleanup_project(project_id):
    delete_project(int(project_id))


@app.cli.command('migrate-workflow-completed-failed-state')
def remove_intersection_dataset():
    migrate_workflow_completed_failed_state()


@app.cli.command('migrate-dataset-job-name')
def add_dataset_job_name():
    migrate_dataset_job_name()


@app.cli.command('migrate-connect-to-test')
def migrate_connect_to_test():
    migrate_connect_to_test()


@app.cli.command('find-variable')
@click.argument('name')
def find_variable(name: str):
    find(name)


@app.cli.command('es-configuration')
def es_configuration():
    es_config()
