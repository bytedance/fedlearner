# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
from http import HTTPStatus
from typing import Optional

from flask_restful import Resource
from google.protobuf import json_format
from google.protobuf.text_format import Parse
from marshmallow import Schema, fields, post_load
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.elements import ColumnElement
from tensorflow.core.example.example_pb2 import Example

from fedlearner_webconsole.proto.serving_pb2 import ServingServiceRemotePlatform
from fedlearner_webconsole.serving import remote
from fedlearner_webconsole.utils.decorators.pp_flask import use_args, use_kwargs

from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.proto import serving_pb2
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, ModelSignatureParserInput
from fedlearner_webconsole.proto.filtering_pb2 import FilterOp, SimpleExpression, FilterExpression
from fedlearner_webconsole.serving.metrics import serving_metrics_emit_counter
from fedlearner_webconsole.serving.participant_fetcher import ParticipantFetcher
from fedlearner_webconsole.serving.runners import ModelSignatureParser, start_query_participant, start_update_model
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import NotFoundException, InvalidArgumentException, \
    InternalException
from fedlearner_webconsole.serving.models import ServingModel, ServingDeployment, ServingNegotiator
from fedlearner_webconsole.serving.services import TensorflowServingService, ServingDeploymentService, \
    ServingModelService
from fedlearner_webconsole.utils import filtering, sorting, flask_utils
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator
from fedlearner_webconsole.utils.flask_utils import make_flask_response, FilterExpField
from fedlearner_webconsole.utils.proto import to_dict

SORT_SUPPORTED_COLUMN = ['created_at']


class ResourceParams(Schema):
    cpu = fields.Str(required=True)
    memory = fields.Str(required=True)
    replicas = fields.Integer(required=True)


class RemotePlatformParams(Schema):
    platform = fields.Str(required=True)
    payload = fields.Str(required=True)


class ServingCreateParams(Schema):
    name = fields.Str(required=True)
    comment = fields.Str(required=False)
    model_id = fields.Integer(required=False)
    model_group_id = fields.Integer(required=False)
    is_local = fields.Boolean(required=False)
    resource = fields.Nested(ResourceParams, required=False)
    remote_platform = fields.Nested(RemotePlatformParams, required=False)

    @post_load
    def make(self, data, **kwargs):
        if 'resource' in data:
            data['resource'] = json_format.ParseDict(data['resource'], serving_pb2.ServingServiceResource())
        if 'remote_platform' in data:
            data['remote_platform'] = json_format.ParseDict(data['remote_platform'],
                                                            serving_pb2.ServingServiceRemotePlatform())
        return data


class ServingUpdateParams(Schema):
    comment = fields.Str(required=False)
    model_id = fields.Integer(required=False)
    model_group_id = fields.Integer(required=False)
    resource = fields.Nested(ResourceParams, required=False)

    @post_load
    def make(self, data, **kwargs):
        if 'resource' in data:
            data['resource'] = json_format.ParseDict(data['resource'], serving_pb2.ServingServiceResource())
        return data


def _build_keyword_query(exp: SimpleExpression) -> ColumnElement:
    return ServingModel.name.ilike(f'%{exp.string_value}%')


class ServingServicesApiV2(Resource):

    FILTER_FIELDS = {
        'name':
            filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'keyword':
            filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.CONTAIN: _build_keyword_query}),
    }

    SORTER_FIELDS = ['created_at']

    def __init__(self):
        self._filter_builder = filtering.FilterBuilder(model_class=ServingModel, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = sorting.SorterBuilder(model_class=ServingModel, supported_fields=self.SORTER_FIELDS)

    @use_kwargs(
        {
            'filter_exp': FilterExpField(data_key='filter', required=False, load_default=None),
            'sorter_exp': fields.String(data_key='order_by', required=False, load_default=None),
        },
        location='query')
    @credentials_required
    def get(self, project_id: int, filter_exp: Optional[FilterExpression], sorter_exp: Optional[str]):
        """Get serving services list
        ---
        tags:
          - serving
        description: get serving services list
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: query
          name: filter
          schema:
            type: string
        - in: query
          name: order_by
          schema:
            type: string
        responses:
          200:
            description: list of service service information
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ServingService'
        """
        service_list = []
        with db.session_scope() as session:
            query = session.query(ServingModel)
            query = query.filter(ServingModel.project_id == project_id)
            if filter_exp is not None:
                try:
                    query = self._filter_builder.build_query(query, filter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter_exp: {str(e)}') from e
            if sorter_exp is not None:
                try:
                    sorter_exp = sorting.parse_expression(sorter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
            else:
                sorter_exp = sorting.SortExpression(field='created_at', is_asc=False)
            query = self._sorter_builder.build_query(query, sorter_exp)
            query = query.outerjoin(ServingDeployment,
                                    ServingDeployment.id == ServingModel.serving_deployment_id).options(
                                        joinedload(ServingModel.serving_deployment))
            all_records = query.all()
        for serving_model in all_records:
            serving_service = serving_model.to_serving_service()
            with db.session_scope() as session:
                serving_model_service = ServingModelService(session)
                serving_model_service.set_resource_and_status_on_ref(serving_service, serving_model)
                serving_model_service.set_is_local_on_ref(serving_service, serving_model)
            service_list.append(serving_service)
        return make_flask_response(data=service_list, status=HTTPStatus.OK)

    @use_args(ServingCreateParams(), location='json_or_form')
    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.SERVING_SERVICE, op_type=Event.CREATE)
    def post(self, body: dict, project_id: int):
        """Create one serving service
        ---
        tags:
          - serving
        description: create one serving service
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/ServingCreateParams'
        responses:
          201:
            description: detail of one serving service
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ServingServiceDetail'
        """
        if 'remote_platform' in body:  # need check sso for third-party serving
            current_sso = flask_utils.get_current_sso()
            if current_sso is None:
                raise InvalidArgumentException('not a sso user')
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            serving_model = serving_model_service.create_from_param(
                project_id=project_id,
                name=body['name'],
                is_local=body['is_local'],
                comment=body['comment'] if 'comment' in body else None,
                model_id=body['model_id'] if 'model_id' in body else None,
                model_group_id=body['model_group_id'] if 'model_group_id' in body else None,
                resource=body['resource'] if 'resource' in body else None,
                remote_platform=body['remote_platform'] if 'remote_platform' in body else None)

            # start async query participant serving status
            if 'is_local' in body and not body['is_local']:
                start_query_participant(session)

            # start async query signature
            if 'remote_platform' not in body:
                runner_item_name = ModelSignatureParser.generate_task_name(serving_model.id, serving_model.name)
                runner_input = RunnerInput(model_signature_parser_input=ModelSignatureParserInput(
                    serving_model_id=serving_model.id))
                ComposerService(session).collect_v2(name=runner_item_name,
                                                    items=[(ItemType.SERVING_SERVICE_PARSE_SIGNATURE, runner_input)])

            # start auto update model runner
            if serving_model.model_group_id is not None:
                start_update_model(session)

            session.commit()
            serving_metrics_emit_counter('serving.create.success', serving_model)
            return make_flask_response(data=serving_model.to_serving_service_detail(), status=HTTPStatus.CREATED)


class ServingServiceApiV2(Resource):

    @use_kwargs({
        'sorter_exp': fields.String(data_key='order_by', required=False, load_default=None),
    },
                location='query')
    @credentials_required
    def get(self, project_id: int, serving_model_id: int, sorter_exp: Optional[str]):
        """Get one serving service
        ---
        tags:
          - serving
        description: get one serving service
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: serving_model_id
          schema:
            type: integer
        - in: query
          name: order_by
          schema:
            type: string
        responses:
          200:
            description: detail of one serving service
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ServingServiceDetail'
        """
        sorter = None
        if sorter_exp is not None:
            try:
                sorter = sorting.parse_expression(sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
        with db.session_scope() as session:
            serving_model_service = ServingModelService(session)
            result = serving_model_service.get_serving_service_detail(serving_model_id, project_id, sorter)
        return make_flask_response(data=result)

    @use_args(ServingUpdateParams(), location='json_or_form')
    @credentials_required
    @emits_event(resource_type=Event.SERVING_SERVICE, op_type=Event.UPDATE)
    def patch(self, body: dict, project_id: int, serving_model_id: int):
        """Modify one serving service
        ---
        tags:
          - serving
        description: get one serving service
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: serving_model_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/ServingUpdateParams'
        responses:
          200:
            description: detail of one serving service
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ServingServiceDetail'
        """
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=serving_model_id, project_id=project_id).options(
                joinedload(ServingModel.serving_deployment)).one_or_none()
            if not serving_model:
                raise NotFoundException(f'Failed to find serving service: {serving_model_id}')
            if 'comment' in body:
                serving_model.comment = body['comment']
            if serving_model.serving_deployment.is_remote_serving():  # need check sso for third-party serving
                current_sso = flask_utils.get_current_sso()
                if current_sso is None:
                    raise InvalidArgumentException('not a sso user')
            need_update_model = False
            if 'model_id' in body:
                need_update_model = ServingModelService(session).update_model(model_id=body['model_id'],
                                                                              model_group_id=None,
                                                                              serving_model=serving_model)
            elif 'model_group_id' in body:
                need_update_model = ServingModelService(session).update_model(model_id=None,
                                                                              model_group_id=body['model_group_id'],
                                                                              serving_model=serving_model)
                start_update_model(session)
            if 'resource' in body:
                current_resource = json.loads(serving_model.serving_deployment.resource)
                new_resource = to_dict(body['resource'])
                if new_resource != current_resource:
                    ServingModelService(session).update_resource(new_resource, serving_model)
            if need_update_model and not serving_model.serving_deployment.is_remote_serving():
                # start async query signature
                runner_item_name = ModelSignatureParser.generate_task_name(serving_model.id, serving_model.name)
                runner_input = RunnerInput(model_signature_parser_input=ModelSignatureParserInput(
                    serving_model_id=serving_model.id))
                ComposerService(session).collect_v2(name=runner_item_name,
                                                    items=[(ItemType.SERVING_SERVICE_PARSE_SIGNATURE, runner_input)])
            session.add(serving_model)
            session.commit()
        serving_metrics_emit_counter('serving.update.success', serving_model)
        return make_flask_response(data=serving_model.to_serving_service_detail())

    @credentials_required
    @emits_event(resource_type=Event.SERVING_SERVICE, op_type=Event.DELETE)
    def delete(self, project_id: int, serving_model_id: int):
        """Delete one serving service
        ---
        tags:
          - serving
        description: delete one serving service
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: serving_model_id
          schema:
            type: integer
        responses:
          204:
            description: delete the sering service successfully
        """
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=serving_model_id,
                                                                  project_id=project_id).one_or_none()
            if not serving_model:
                serving_metrics_emit_counter('serving.delete.db_error', serving_model)
                raise NotFoundException(f'Failed to find serving model: {serving_model_id}')
            ServingModelService(session).delete_serving_service(serving_model)
            session.commit()
        serving_metrics_emit_counter('serving.delete.success', serving_model)
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class ServingServiceInferenceApiV2(Resource):

    @use_args({'input_data': fields.String(required=True, help='serving input data')}, location='json')
    @credentials_required
    def post(self, body: dict, project_id: int, serving_model_id: int):
        """Get inference result from a serving service
        ---
        tags:
          - serving
        description: get inference result from a serving service
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: serving_model_id
          schema:
            type: integer
        requestBody:
          required: true
          description: input data to do inference
          content:
            application/json:
              schema:
                type: string
        responses:
          200:
            description: inference result
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.PredictResponse'
        """
        try:
            input_data = Parse(body['input_data'], Example())
        except Exception as err:
            serving_metrics_emit_counter('serving.inference.invalid_arguments')
            raise InvalidArgumentException(f'Failed to parse inference input: {serving_model_id}') from err
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=serving_model_id,
                                                                  project_id=project_id).one_or_none()
            if not serving_model:
                serving_metrics_emit_counter('serving.inference.db_error')
                raise NotFoundException(f'Failed to find serving model: {serving_model_id}')
            deployment_name = serving_model.serving_deployment.deployment_name
        tf_serving_service = TensorflowServingService(deployment_name)
        extend_input = {}
        with db.session_scope() as session:
            serving_negotiator = session.query(ServingNegotiator).filter_by(
                serving_model_id=serving_model_id).one_or_none()
            if serving_negotiator is not None:
                extend_input.update(ParticipantFetcher(session).fetch(serving_negotiator, '1'))
        output = tf_serving_service.get_model_inference_output(input_data, extend_input)
        if 'Error' in output:
            serving_metrics_emit_counter('serving.inference.rpc_error')
            raise InternalException(f'Failed to do inference: {output}')
        serving_metrics_emit_counter('serving.inference.success')
        return make_flask_response(data=output)


class ServingServiceInstanceLogApiV2(Resource):

    @use_args({'tail_lines': fields.Integer(required=True, help='tail lines is required')}, location='query')
    @credentials_required
    def get(self, body: dict, project_id: int, serving_model_id: int, instance_name: str):
        """Get inference result from a serving service
        ---
        tags:
          - serving
        description: get inference result from a serving service
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: serving_model_id
          schema:
            type: integer
        - in: path
          name: instance_name
          schema:
            type: string
        - in: query
          name: tail_lines
          schema:
            type: integer
          description: lines of log
        responses:
          200:
            description: inference result
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        with db.session_scope() as session:
            serving_model = session.query(ServingModel).filter_by(id=serving_model_id,
                                                                  project_id=project_id).one_or_none()
            if not serving_model:
                serving_metrics_emit_counter('serving.logs.db_error')
                raise NotFoundException(f'Failed to find serving model: {serving_model_id}')
        tail_lines = body['tail_lines']
        result = ServingDeploymentService.get_pod_log(instance_name, tail_lines)
        return make_flask_response(data=result)


class ServingServiceRemotePlatformsApi(Resource):

    @credentials_required
    def get(self, project_id: int):
        """Get supported third-party serving platform
        ---
        tags:
          - serving
        description: get supported third-party serving platform
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            description: list of supported serving remote platform
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ServingServiceRemotePlatform'
        """
        result_list = []
        current_sso = flask_utils.get_current_sso()
        if current_sso is None:
            return make_flask_response(data=result_list)
        for key, value in remote.supported_remote_serving.items():
            support_platform = ServingServiceRemotePlatform(platform=key)
            result_list.append(support_platform)
        return make_flask_response(data=result_list)


def initialize_serving_services_apis(api):
    api.add_resource(ServingServicesApiV2, '/projects/<int:project_id>/serving_services')
    api.add_resource(ServingServiceApiV2, '/projects/<int:project_id>/serving_services/<int:serving_model_id>')
    api.add_resource(ServingServiceInferenceApiV2,
                     '/projects/<int:project_id>/serving_services/<int:serving_model_id>/inference')
    api.add_resource(
        ServingServiceInstanceLogApiV2, '/projects/<int:project_id>/serving_services/<int:serving_model_id>/instances'
        '/<string:instance_name>/log')
    api.add_resource(ServingServiceRemotePlatformsApi, '/projects/<int:project_id>/serving_services/remote_platforms')

    # if a schema is used, one has to append it to schema_manager so Swagger knows there is a schema available
    schema_manager.append(ServingCreateParams)
    schema_manager.append(ServingUpdateParams)
