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
# pylint: disable=wrong-import-position, global-statement
import logging
import logging.config
import os
import traceback

from http import HTTPStatus
from flask import Flask, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from envs import Envs
from fedlearner_webconsole.utils import metrics

jwt = JWTManager()

from fedlearner_webconsole.auth.apis import initialize_auth_apis
from fedlearner_webconsole.project.apis import initialize_project_apis
from fedlearner_webconsole.workflow_template.apis \
    import initialize_workflow_template_apis
from fedlearner_webconsole.workflow.apis import initialize_workflow_apis
from fedlearner_webconsole.dataset.apis import initialize_dataset_apis
from fedlearner_webconsole.job.apis import initialize_job_apis
from fedlearner_webconsole.setting.apis import initialize_setting_apis
from fedlearner_webconsole.mmgr.apis import initialize_mmgr_apis
from fedlearner_webconsole.debug.apis import initialize_debug_apis
from fedlearner_webconsole.sparkapp.apis import initialize_sparkapps_apis
from fedlearner_webconsole.rpc.server import rpc_server
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (make_response,
                                              WebConsoleApiException,
                                              InvalidArgumentException,
                                              NotFoundException)
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.utils.k8s_watcher import k8s_watcher
from fedlearner_webconsole.auth.models import User, Session
from fedlearner_webconsole.composer.composer import composer
from logging_config import LOGGING_CONFIG


def _handle_bad_request(error):
    """Handles the bad request raised by reqparse"""
    if not isinstance(error, WebConsoleApiException):
        # error.data.message contains the details raised by reqparse
        details = None
        if error.data is not None:
            details = error.data['message']
        return make_response(InvalidArgumentException(details))
    return error


def _handle_not_found(error):
    """Handles the not found exception raised by framework"""
    if not isinstance(error, WebConsoleApiException):
        return make_response(NotFoundException())
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
    response = jsonify(code=HTTPStatus.UNAUTHORIZED, msg=reason)
    return response, HTTPStatus.UNAUTHORIZED


@jwt.invalid_token_loader
def _handle_invalid_jwt_request(reason):
    response = jsonify(code=HTTPStatus.UNPROCESSABLE_ENTITY, msg=reason)
    return response, HTTPStatus.UNPROCESSABLE_ENTITY


@jwt.expired_token_loader
def _handle_token_expired_request(expired_token):
    response = jsonify(code=HTTPStatus.UNAUTHORIZED, msg='Token has expired')
    return response, HTTPStatus.UNAUTHORIZED


@jwt.user_lookup_loader
def user_lookup_callback(jwt_header, jwt_data):
    del jwt_header  # Unused by user load.

    identity = jwt_data['sub']
    return User.query.filter_by(username=identity).one_or_none()


@jwt.token_in_blocklist_loader
def check_if_token_invalid(jwt_header, jwt_data):
    del jwt_header  # unused by check_if_token_invalid

    jti = jwt_data['jti']
    session = Session.query.filter_by(jti=jti).first()
    return session is None


def create_app(config):
    # format logging
    logging.config.dictConfig(LOGGING_CONFIG)

    app = Flask('fedlearner_webconsole')
    app.config.from_object(config)

    jwt.init_app(app)

    # Error handlers
    app.register_error_handler(400, _handle_bad_request)
    app.register_error_handler(404, _handle_not_found)
    app.register_error_handler(WebConsoleApiException, make_response)
    app.register_error_handler(Exception, _handle_uncaught_exception)

    # TODO(wangsen.0914): This will be removed sooner!
    db.init_app(app)

    api = Api(prefix='/api/v2')
    initialize_auth_apis(api)
    initialize_project_apis(api)
    initialize_workflow_template_apis(api)
    initialize_workflow_apis(api)
    initialize_job_apis(api)
    initialize_dataset_apis(api)
    initialize_setting_apis(api)
    initialize_mmgr_apis(api)
    initialize_sparkapps_apis(api)
    if os.environ.get('FLASK_ENV') != 'production' or Envs.DEBUG:
        initialize_debug_apis(api)
    # A hack that use our customized error handlers
    # Ref: https://github.com/flask-restful/flask-restful/issues/280
    handle_exception = app.handle_exception
    handle_user_exception = app.handle_user_exception
    api.init_app(app)
    app.handle_exception = handle_exception
    app.handle_user_exception = handle_user_exception

    # Inits k8s related stuff first since something in composer
    # may depend on it
    if Envs.FLASK_ENV == 'production' or Envs.K8S_CONFIG_PATH is not None:
        k8s_watcher.start()

    if app.config.get('START_GRPC_SERVER', True):
        rpc_server.stop()
        rpc_server.start(app)
    if app.config.get('START_SCHEDULER', True):
        scheduler.stop()
        scheduler.start(app)
    if app.config.get('START_COMPOSER', True):
        with app.app_context():
            composer.run(db_engine=db.get_engine())

    metrics.emit_counter('create_app', 1)
    return app
