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
import logging
from http import HTTPStatus
from pathlib import Path
from flask_restful import Resource
from google.protobuf.json_format import ParseDict, ParseError
from marshmallow import fields

from fedlearner_webconsole.k8s.k8s_client import k8s_client
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.proto.setting_pb2 import SystemVariables, SettingPb
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required, use_kwargs, use_args
from fedlearner_webconsole.setting.service import DashboardService, SettingService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (NotFoundException, NoAccessException, InvalidArgumentException)
from fedlearner_webconsole.utils.flask_utils import make_flask_response
from fedlearner_webconsole.flag.models import Flag

_POD_NAMESPACE = 'default'
# Ref: https://stackoverflow.com/questions/46046110/
#      how-to-get-the-current-namespace-in-a-pod
_k8s_namespace_file = Path('/var/run/secrets/kubernetes.io/serviceaccount/namespace')
if _k8s_namespace_file.is_file():
    _POD_NAMESPACE = _k8s_namespace_file.read_text(encoding='utf-8')

_SPECIAL_KEYS = ['webconsole_image', 'system_info', 'system_variables']


class SettingApi(Resource):

    @credentials_required
    @admin_required
    def _get_webconsole_image(self) -> SettingPb:
        try:
            deployment = k8s_client.get_deployment(name='fedlearner-web-console-v2')
            image = deployment.spec.template.spec.containers[0].image
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f'settings: get deployment: {str(e)}')
            image = None
        return SettingPb(
            uniq_key='webconsole_image',
            value=image,
        )

    @credentials_required
    @admin_required
    def _get_system_variables(self) -> SystemVariables:
        with db.session_scope() as session:
            return SettingService(session).get_system_variables()

    def get(self, key: str):
        """Gets a specific setting.
        ---
        tags:
          - system
        description: gets a specific setting.
        parameters:
        - in: path
          name: key
          schema:
            type: string
          required: true
        responses:
          200:
            description: the setting
            content:
              application/json:
                schema:
                  oneOf:
                    - $ref: '#/definitions/fedlearner_webconsole.proto.SettingPb'
                    - $ref: '#/definitions/fedlearner_webconsole.proto.SystemVariables'
                    - $ref: '#/definitions/fedlearner_webconsole.proto.SystemInfo'
        """
        if key == 'webconsole_image':
            return make_flask_response(self._get_webconsole_image())

        if key == 'system_variables':
            return make_flask_response(self._get_system_variables())

        if key == 'system_info':
            return make_flask_response(SettingService.get_system_info())

        setting = None
        if key not in _SPECIAL_KEYS:
            with db.session_scope() as session:
                setting = SettingService(session).get_setting(key)
        if setting is None:
            raise NotFoundException(message=f'Failed to find setting {key}')
        return make_flask_response(setting.to_proto())

    @credentials_required
    @admin_required
    @use_kwargs({'value': fields.String(required=True)})
    def put(self, key: str, value: str):
        """Updates a specific setting.
        ---
        tags:
          - system
        description: updates a specific setting.
        parameters:
        - in: path
          name: key
          schema:
            type: string
          required: true
        - in: body
          name: body
          schema:
            type: object
            properties:
              value:
                type: str
                required: true
        responses:
          200:
            description: logs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        if key in _SPECIAL_KEYS:
            raise NoAccessException(message=f'Not able to update {key}')

        with db.session_scope() as session:
            setting = SettingService(session).create_or_update_setting(key, value)
            return make_flask_response(setting.to_proto())


class UpdateSystemVariablesApi(Resource):

    @credentials_required
    @admin_required
    @use_args({'variables': fields.List(fields.Dict())})
    def post(self, params: dict):
        """Updates system variables.
        ---
        tags:
          - system
        description: updates all system variables.
        parameters:
        - in: body
          name: body
          schema:
            $ref: '#/definitions/fedlearner_webconsole.proto.SystemVariables'
        responses:
          200:
            description: updated system variables
            content:
              application/json:
                schema:
                    $ref: '#/definitions/fedlearner_webconsole.proto.SystemVariables'
        """
        try:
            system_variables = ParseDict(params, SystemVariables())
        except ParseError as e:
            raise InvalidArgumentException(details=str(e)) from e
        with db.session_scope() as session:
            # TODO(xiangyuxuan.prs): check fixed flag
            SettingService(session).set_system_variables(system_variables)
            session.commit()
            return make_flask_response(system_variables)


class UpdateImageApi(Resource):

    @credentials_required
    @admin_required
    @use_kwargs({'webconsole_image': fields.String(required=True)})
    def post(self, webconsole_image: str):
        """Updates webconsole image.
        ---
        tags:
          - system
        description: updates webconsole image.
        parameters:
        - in: body
          name: body
          schema:
            type: object
            properties:
              image_uri:
                type: string
                required: true
        responses:
          204:
            description: updated successfully
        """
        deployment = k8s_client.get_deployment('fedlearner-web-console-v2')
        spec = deployment.spec
        spec.template.spec.containers[0].image = webconsole_image
        metadata = deployment.metadata
        k8s_client.create_or_update_deployment(metadata=metadata,
                                               spec=spec,
                                               name=metadata.name,
                                               namespace=metadata.namespace)
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class SystemPodLogsApi(Resource):

    @credentials_required
    @admin_required
    @use_kwargs({'tail_lines': fields.Integer(required=True)}, location='query')
    def get(self, pod_name: str, tail_lines: int):
        """Gets webconsole pod logs.
        ---
        tags:
          - system
        description: gets webconsole pod logs.
        parameters:
        - in: path
          name: pod_name
          schema:
            type: string
          required: true
        - in: query
          name: tail_lines
          schema:
            type: integer
          required: true
        responses:
          200:
            description: logs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        return make_flask_response(
            k8s_client.get_pod_log(name=pod_name, namespace=_POD_NAMESPACE, tail_lines=tail_lines).split('\n'))


class SystemPodsApi(Resource):

    @credentials_required
    @admin_required
    def get(self):
        """Gets webconsole pods.
        ---
        tags:
          - system
        description: gets webconsole pods.
        responses:
          200:
            description: name list of pods
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        webconsole_v2_pod_list = list(
            map(lambda pod: pod.metadata.name,
                k8s_client.get_pods(_POD_NAMESPACE, 'app.kubernetes.io/instance=fedlearner-web-console-v2').items))
        return make_flask_response(webconsole_v2_pod_list)


class VersionsApi(Resource):
    # This is a system-based api, no JWT-Token for now.
    def get(self):
        """Gets the version info.
        ---
        tags:
          - system
        description: gets the version info.
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ApplicationVersion'
        """
        return make_flask_response(SettingService.get_application_version().to_proto())


class DashboardsApi(Resource):

    @credentials_required
    @admin_required
    def get(self):
        """Get dashboard information API
        ---
        tags:
          - system
        description: Get dashboard information API
        responses:
          200:
            description: a list of dashboard information. Note that the following dashboard ['overview'] is available.
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DashboardInformation'
          500:
            description: dashboard setup is wrong, please check.
            content:
              appliction/json:
                schema:
                  type: object
                  properties:
                    code:
                      type: integer
                    message:
                      type: string
        """
        if not Flag.DASHBOARD_ENABLED.value:
            raise NoAccessException('if you want to view dashboard, please enable flag `DASHBOARD_ENABLED`')
        return make_flask_response(DashboardService().get_dashboards())


def initialize_setting_apis(api):
    api.add_resource(UpdateSystemVariablesApi, '/settings:update_system_variables')
    api.add_resource(UpdateImageApi, '/settings:update_image')
    api.add_resource(SettingApi, '/settings/<string:key>')
    api.add_resource(VersionsApi, '/versions')
    api.add_resource(SystemPodLogsApi, '/system_pods/<string:pod_name>/logs')
    api.add_resource(SystemPodsApi, '/system_pods/name')
    api.add_resource(DashboardsApi, '/dashboards')
