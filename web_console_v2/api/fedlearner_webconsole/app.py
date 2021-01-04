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
import logging
import traceback

from http import HTTPStatus
from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_restful import Api
from flask_jwt_extended import JWTManager

migrate = Migrate()
jwt = JWTManager()

from fedlearner_webconsole.auth.apis import initialize_auth_apis
from fedlearner_webconsole.project.apis import initialize_project_apis
from fedlearner_webconsole.workflow_template.apis \
    import initialize_workflow_template_apis
from fedlearner_webconsole.workflow.apis import initialize_workflow_apis
from fedlearner_webconsole.rpc.server import rpc_server
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (
    make_response, WebConsoleApiException, InvalidArgumentException)
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.scheduler.job_scheduler import job_scheduler

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


def create_app(config):
    app = Flask('fedlearner_webconsole')
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Error handlers
    app.register_error_handler(400, _handle_bad_request)
    app.register_error_handler(WebConsoleApiException, make_response)
    app.register_error_handler(Exception, _handle_uncaught_exception)

    api = Api(prefix='/api/v2')
    initialize_auth_apis(api)
    initialize_project_apis(api)
    initialize_workflow_template_apis(api)
    initialize_workflow_apis(api)
    # A hack that use our customized error handlers
    # Ref: https://github.com/flask-restful/flask-restful/issues/280
    handle_exception = app.handle_exception
    handle_user_exception = app.handle_user_exception
    api.init_app(app)
    app.handle_exception = handle_exception
    app.handle_user_exception = handle_user_exception
    # TODO: flask will start twice, but following stop code does not work.
    #  Separate the server and schedulers to a new process to fix the bug.
    if app.config.get('START_GRPC_SERVER', True):
        rpc_server.stop()
        rpc_server.start(app)

    if app.config.get('START_SCHEDULER', True):
        scheduler.stop()
        scheduler.start(app)

    if app.config.get('START_JOB_SCHEDULER', True):
        job_scheduler.stop()
        job_scheduler.start(app)

    return app
