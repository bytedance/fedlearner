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
from http import HTTPStatus
import logging

from flask_restful import Api, Resource
from marshmallow import Schema, fields, post_load
from webargs.flaskparser import use_args, use_kwargs

from fedlearner_webconsole.sparkapp.schema import SparkAppConfig
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.sparkapp.service import SparkAppService
from fedlearner_webconsole.exceptions import (InternalException, NotFoundException)
from fedlearner_webconsole.utils.flask_utils import make_flask_response
from fedlearner_webconsole.swagger.models import schema_manager


class SparkAppPodParameter(Schema):
    cores = fields.Integer(required=True)
    memory = fields.String(required=True)
    instances = fields.Integer(required=False, load_default=1)
    core_limit = fields.String(required=False)
    volume_mounts = fields.List(fields.Dict(fields.String, fields.String), required=False)
    envs = fields.Dict(fields.String, fields.String)


class SparkAppCreateParameter(Schema):
    name = fields.String(required=True)
    files = fields.String(required=False, load_default=None)
    files_path = fields.String(required=False, load_default=None)
    image_url = fields.String(required=False, load_default=None)
    volumes = fields.List(fields.Dict(fields.String, fields.String), required=False, load_default=[])
    driver_config = fields.Nested(SparkAppPodParameter)
    executor_config = fields.Nested(SparkAppPodParameter)
    py_files = fields.List(fields.String, required=False, load_default=[])
    command = fields.List(fields.String, required=False, load_default=[])
    main_application = fields.String(required=True)

    @post_load
    def make_spark_app_config(self, data, **kwargs):
        del kwargs
        return SparkAppConfig.from_dict(data)


class SparkAppsApi(Resource):

    @credentials_required
    @use_args(SparkAppCreateParameter())
    def post(self, config: SparkAppConfig):
        """Create sparkapp
        ---
        tags:
          - sparkapp
        description: Create sparkapp
        parameters:
        - in: body
          name: body
          schema:
            $ref: '#/definitions/SparkAppCreateParameter'
        responses:
          201:
            description: The sparkapp is created
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.SparkAppInfo'
        """
        service = SparkAppService()
        return make_flask_response(data=service.submit_sparkapp(config=config), status=HTTPStatus.CREATED)


class SparkAppApi(Resource):

    @credentials_required
    def get(self, sparkapp_name: str):
        """Get sparkapp status
        ---
        tags:
          - sparkapp
        description: Get sparkapp status
        parameters:
        - in: path
          name: sparkapp_name
          schema:
            type: string
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.SparkAppInfo'
        """
        service = SparkAppService()
        return make_flask_response(data=service.get_sparkapp_info(sparkapp_name))

    @credentials_required
    def delete(self, sparkapp_name: str):
        """Delete a sparkapp whether the existence of sparkapp
        ---
        tags:
          - sparkapp
        description: Delete a sparkapp whether the existence of sparkapp
        parameters:
        - in: path
          name: sparkapp_name
          schema:
            type: string
        responses:
          204:
            description: finish sparkapp deletion
        """
        service = SparkAppService()
        try:
            service.delete_sparkapp(sparkapp_name)
        except NotFoundException:
            logging.warning(f'[sparkapp] could not find sparkapp {sparkapp_name}')

        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class SparkAppLogApi(Resource):

    @credentials_required
    @use_kwargs({'lines': fields.Integer(required=True, help='lines is required')}, location='query')
    def get(self, sparkapp_name: str, lines: int):
        """Get sparkapp logs
        ---
        tags:
          - sparkapp
        description: Get sparkapp logs
        parameters:
        - in: path
          name: sparkapp_name
          schema:
            type: string
        - in: query
          name: lines
          schema:
            type: integer
        responses:
          200:
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        max_limit = 10000
        if lines is None or lines > max_limit:
            lines = max_limit
        service = SparkAppService()
        try:
            return make_flask_response(data=service.get_sparkapp_log(sparkapp_name, lines))
        except Exception as e:  # pylint: disable=broad-except)
            raise InternalException(details=f'error {e}') from e


def initialize_sparkapps_apis(api: Api):
    api.add_resource(SparkAppsApi, '/sparkapps')
    api.add_resource(SparkAppApi, '/sparkapps/<string:sparkapp_name>')
    api.add_resource(SparkAppLogApi, '/sparkapps/<string:sparkapp_name>/log')

    schema_manager.append(SparkAppCreateParameter)
