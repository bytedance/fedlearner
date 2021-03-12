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
# pylint: disable=wrong-import-position, global-statement
import importlib
import logging
import os
import traceback

from http import HTTPStatus
from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_restful import Api
from flask_jwt_extended import JWTManager

from fedlearner_webconsole import envs
from fedlearner_webconsole.utils.file_manager import build_hdfs_client
from fedlearner_webconsole.utils.es import es

migrate = Migrate()
jwt = JWTManager()

from fedlearner_webconsole.auth.apis import initialize_auth_apis
from fedlearner_webconsole.project.apis import initialize_project_apis
from fedlearner_webconsole.workflow_template.apis \
    import initialize_workflow_template_apis
from fedlearner_webconsole.workflow.apis import initialize_workflow_apis
from fedlearner_webconsole.dataset.apis import initialize_dataset_apis
from fedlearner_webconsole.job.apis import initialize_job_apis
from fedlearner_webconsole.setting.apis import initialize_setting_apis
from fedlearner_webconsole.rpc.server import rpc_server
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (
    make_response, WebConsoleApiException, InvalidArgumentException)
from fedlearner_webconsole.scheduler.scheduler import scheduler

def _handle_bad_request(error):
    """Handles the bad request raised by reqparse"""
    if not isinstance(error, WebConsoleApiException):
        # error.data.message contains the details raised by reqparse
        details = None
        if error.data is not None:
            details = error.data['message']
        return make_response(InvalidArgumentException(details))
    return error


def _handle_uncaught_exception(error):
    """A fallback catcher for all exceptions."""
    logging.error('Uncaught exception %s, stack trace:\n %s', str(error),
                  traceback.format_exc())
    response = jsonify(
        code=500,
        msg='Unknown error',
    )
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    return response


@jwt.unauthorized_loader
def _handle_unauthorized_request(reason):
    response = jsonify(
        code=HTTPStatus.UNAUTHORIZED,
        msg=reason
    )
    return response, HTTPStatus.UNAUTHORIZED


@jwt.invalid_token_loader
def _handle_invalid_jwt_request(reason):
    response = jsonify(
        code=HTTPStatus.UNPROCESSABLE_ENTITY,
        msg=reason
    )
    return response, HTTPStatus.UNPROCESSABLE_ENTITY


@jwt.expired_token_loader
def _handle_token_expired_request(expired_token):
    response = jsonify(
        code=HTTPStatus.UNAUTHORIZED,
        msg='Token has expired'
    )
    return response, HTTPStatus.UNAUTHORIZED


def create_app(config):
    before_hook_path = os.getenv(
        'FEDLEARNER_WEBCONSOLE_BEFORE_APP_START')
    if before_hook_path:
        module_path, func_name = before_hook_path.split(':')
        module = importlib.import_module(module_path)
        # Dynamically run the function
        getattr(module, func_name)()

    app = Flask('fedlearner_webconsole')
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    es.init_app(app)

    # Error handlers
    app.register_error_handler(400, _handle_bad_request)
    app.register_error_handler(WebConsoleApiException, make_response)
    app.register_error_handler(Exception, _handle_uncaught_exception)

    api = Api(prefix='/api/v2')
    initialize_auth_apis(api)
    initialize_project_apis(api)
    initialize_workflow_template_apis(api)
    initialize_workflow_apis(api)
    initialize_job_apis(api)
    initialize_dataset_apis(api)
    initialize_setting_apis(api)
    # A hack that use our customized error handlers
    # Ref: https://github.com/flask-restful/flask-restful/issues/280
    handle_exception = app.handle_exception
    handle_user_exception = app.handle_user_exception
    api.init_app(app)
    app.handle_exception = handle_exception
    app.handle_user_exception = handle_user_exception

    if app.config.get('START_GRPC_SERVER', True):
        rpc_server.stop()
        rpc_server.start(app)

    if app.config.get('START_SCHEDULER', True):
        scheduler.stop()
        scheduler.start(app)

    return app


if envs.SUPPORT_HDFS:
    build_hdfs_client()
