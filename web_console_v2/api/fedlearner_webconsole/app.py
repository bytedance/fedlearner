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
# pylint: disable=wrong-import-position, global-statement
import logging
import logging.config

from http import HTTPStatus
from json import load
from pathlib import Path

from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flasgger import APISpec, Swagger
from flask import Flask, jsonify
from flask_restful import Api
from marshmallow import ValidationError
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from webargs.flaskparser import parser

from envs import Envs
from fedlearner_webconsole.utils.hooks import pre_start_hook
from fedlearner_webconsole.composer.apis import initialize_composer_apis
from fedlearner_webconsole.cleanup.apis import initialize_cleanup_apis
from fedlearner_webconsole.audit.apis import initialize_audit_apis
from fedlearner_webconsole.auth.services import UserService
from fedlearner_webconsole.e2e.apis import initialize_e2e_apis
from fedlearner_webconsole.flag.apis import initialize_flags_apis
from fedlearner_webconsole.iam.apis import initialize_iams_apis
from fedlearner_webconsole.iam.client import create_iams_for_user
from fedlearner_webconsole.middleware.middlewares import flask_middlewares
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils import metrics, const
from fedlearner_webconsole.auth.apis import initialize_auth_apis
from fedlearner_webconsole.project.apis import initialize_project_apis
from fedlearner_webconsole.participant.apis import initialize_participant_apis
from fedlearner_webconsole.utils.decorators.pp_flask import parser as custom_parser
from fedlearner_webconsole.utils.swagger import normalize_schema
from fedlearner_webconsole.workflow_template.apis import initialize_workflow_template_apis
from fedlearner_webconsole.workflow.apis import initialize_workflow_apis
from fedlearner_webconsole.dataset.apis import initialize_dataset_apis
from fedlearner_webconsole.job.apis import initialize_job_apis
from fedlearner_webconsole.setting.apis import initialize_setting_apis
from fedlearner_webconsole.mmgr.model_apis import initialize_mmgr_model_apis
from fedlearner_webconsole.mmgr.model_job_apis import initialize_mmgr_model_job_apis
from fedlearner_webconsole.mmgr.model_job_group_apis import initialize_mmgr_model_job_group_apis
from fedlearner_webconsole.algorithm.apis import initialize_algorithm_apis
from fedlearner_webconsole.debug.apis import initialize_debug_apis
from fedlearner_webconsole.serving.apis import initialize_serving_services_apis
from fedlearner_webconsole.sparkapp.apis import initialize_sparkapps_apis
from fedlearner_webconsole.file.apis import initialize_files_apis
from fedlearner_webconsole.tee.apis import initialize_tee_apis
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import make_response, WebConsoleApiException, InvalidArgumentException
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.k8s.k8s_watcher import k8s_watcher
from logging_config import get_logging_config
from werkzeug.exceptions import HTTPException


@custom_parser.error_handler
@parser.error_handler
def handle_request_parsing_error(validation_error: ValidationError, *args, **kwargs):
    raise InvalidArgumentException(details=validation_error.messages)


def _handle_bad_request(error):
    """Handles the bad request raised by reqparse"""
    if not isinstance(error, WebConsoleApiException):
        # error.data.message contains the details raised by reqparse
        details = None
        if error.data is not None:
            details = error.data['message']
        return make_response(InvalidArgumentException(details))
    return error


def _handle_wsgi_exception(error: HTTPException):
    logging.exception('Wsgi exception: %s', str(error))
    response = jsonify(
        code=error.code,
        msg=str(error),
    )
    response.status_code = error.code
    return response


def _handle_uncaught_exception(error):
    """A fallback catcher for all exceptions."""
    logging.exception('Uncaught exception %s', str(error))
    response = jsonify(
        code=500,
        msg='Unknown error',
    )
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    return response


def _initial_iams_for_users(session: Session):
    inspector = inspect(db.engine)
    if inspector.has_table('users_v2'):
        try:
            users = UserService(session).get_all_users()
            for u in users:
                create_iams_for_user(u)
        except Exception as e:  # pylint: disable=broad-except
            logging.warning('Initial iams failed, will be OK after db migration.')


def _init_swagger(app: Flask):
    openapi_version = '3.0.3'
    spec = APISpec(title='FedLearner WebConsole API Documentation',
                   version=SettingService.get_application_version().version.version,
                   openapi_version=openapi_version,
                   plugins=[FlaskPlugin(), MarshmallowPlugin()])
    schemas = schema_manager.get_schemas()
    template = spec.to_flasgger(app, definitions=schemas, paths=[*app.view_functions.values()])
    app.config['SWAGGER'] = {'title': 'FedLearner WebConsole API Documentation', 'uiversion': 3}
    for path in (Path(__file__).parent / 'proto' / 'jsonschemas').glob('**/*.json'):
        with open(path, mode='r', encoding='utf-8') as file:
            definitions = load(file)['definitions']
            definitions = normalize_schema(definitions, Path(path))
            template['components']['schemas'] = {**template['components']['schemas'], **definitions}
    template['definitions'] = template['components']['schemas']
    Swagger(app,
            template=template,
            config={
                'url_prefix': Envs.SWAGGER_URL_PREFIX,
                'openapi': openapi_version
            },
            merge=True)


def create_app(config):
    pre_start_hook()
    # format logging
    logging.config.dictConfig(get_logging_config())

    app = Flask('fedlearner_webconsole', root_path=Envs.BASE_DIR)
    app.config.from_object(config)

    # Error handlers
    app.register_error_handler(400, _handle_bad_request)
    app.register_error_handler(WebConsoleApiException, make_response)
    app.register_error_handler(HTTPException, _handle_wsgi_exception)
    app.register_error_handler(Exception, _handle_uncaught_exception)
    # TODO(xiangyuxuan.prs): Initial iams for all existed users, remove when not using memory-iams
    with db.session_scope() as session:
        _initial_iams_for_users(session)
    api = Api(prefix=const.API_VERSION)
    initialize_composer_apis(api)
    initialize_cleanup_apis(api)
    initialize_auth_apis(api)
    initialize_project_apis(api)
    initialize_participant_apis(api)
    initialize_workflow_template_apis(api)
    initialize_workflow_apis(api)
    initialize_job_apis(api)
    initialize_dataset_apis(api)
    initialize_setting_apis(api)
    initialize_mmgr_model_apis(api)
    initialize_mmgr_model_job_apis(api)
    initialize_mmgr_model_job_group_apis(api)
    initialize_algorithm_apis(api)
    initialize_sparkapps_apis(api)
    initialize_files_apis(api)
    initialize_flags_apis(api)
    initialize_serving_services_apis(api)
    initialize_iams_apis(api)
    initialize_e2e_apis(api)
    initialize_tee_apis(api)
    if Envs.FLASK_ENV != 'production' or Envs.DEBUG:
        initialize_debug_apis(api)
    initialize_audit_apis(api)
    # A hack that use our customized error handlers
    # Ref: https://github.com/flask-restful/flask-restful/issues/280
    handle_exception = app.handle_exception
    handle_user_exception = app.handle_user_exception
    api.init_app(app)
    app.handle_exception = handle_exception
    app.handle_user_exception = handle_user_exception
    if Envs.FLASK_ENV != 'production' or Envs.DEBUG:
        _init_swagger(app)
    # Inits k8s related stuff first since something in composer
    # may depend on it
    if app.config.get('START_K8S_WATCHER', True):
        k8s_watcher.start()
    if app.config.get('START_SCHEDULER', True):
        scheduler.stop()
        scheduler.start()

    metrics.emit_store('create_app', 1)
    app = flask_middlewares.init_app(app)
    return app
