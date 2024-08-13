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
import logging
import tempfile
from http import HTTPStatus
from flask import send_file
from flask_restful import Resource
from typing import Optional, List
from webargs.flaskparser import use_args, use_kwargs
from marshmallow import Schema, post_load, fields, validate
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.services import BatchService
from fedlearner_webconsole.exceptions import NotFoundException, ResourceConflictException, InternalException, \
    InvalidArgumentException, NoAccessException, UnauthorizedException
from fedlearner_webconsole.utils.sorting import SorterBuilder, SortExpression, parse_expression
from fedlearner_webconsole.workflow.models import Workflow, WorkflowExternalState
from fedlearner_webconsole.workflow_template.service import dict_to_workflow_definition
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.mmgr.controller import CreateModelJob, start_model_job, stop_model_job, \
    ModelJobController, ModelJobGroupController
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobGroup, ModelJobType, ModelJobRole, \
    is_federated, AuthStatus, GroupAutoUpdateStatus, GroupAuthFrontendStatus, ModelJobStatus
from fedlearner_webconsole.mmgr.service import ModelJobService, ModelJobGroupService, get_sys_template_id, \
    get_model_job, get_project, get_participant
from fedlearner_webconsole.mmgr.model_job_configer import ModelJobConfiger, set_load_model_name
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.flask_utils import make_flask_response, get_current_user, FilterExpField, \
    FilterExpression
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterOp, SimpleExpression, FilterBuilder
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.mmgr_pb2 import PeerModelJobPb, ModelJobGlobalConfig
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from fedlearner_webconsole.flag.models import Flag


def _check_model_job_global_config_enable(project_id: int) -> bool:
    with db.session_scope() as session:
        participants = session.query(Project).get(project_id).participants
    flag = True
    for p in participants:
        client = SystemServiceClient.from_participant(domain_name=p.domain_name)
        resp = client.list_flags()
        if not resp.get(Flag.MODEL_JOB_GLOBAL_CONFIG_ENABLED.name):
            flag = False
    return flag


class CreateModelJobParams(Schema):
    name = fields.Str(required=True)
    group_id = fields.Integer(required=False, load_default=None)
    model_job_type = fields.Str(required=True,
                                validate=validate.OneOf([
                                    ModelJobType.TRAINING.name, ModelJobType.EVALUATION.name,
                                    ModelJobType.PREDICTION.name
                                ]))
    algorithm_type = fields.Str(required=True,
                                validate=validate.OneOf([
                                    AlgorithmType.TREE_VERTICAL.name, AlgorithmType.NN_VERTICAL.name,
                                    AlgorithmType.NN_HORIZONTAL.name
                                ]))
    algorithm_id = fields.Integer(required=False, load_default=None)
    eval_model_job_id = fields.Integer(required=False, load_default=None)
    model_id = fields.Integer(required=False, load_default=None)
    dataset_id = fields.Integer(required=False, load_default=None)
    data_batch_id = fields.Integer(required=False, load_default=None)
    config = fields.Dict(required=False, load_default={})
    comment = fields.Str(required=False, load_default=None)
    global_config = fields.Dict(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['config'] = dict_to_workflow_definition(data['config'])
        data['model_job_type'] = ModelJobType[data['model_job_type']]
        data['algorithm_type'] = AlgorithmType[data['algorithm_type']]
        if data.get('eval_model_job_id') is not None:
            with db.session_scope() as session:
                model = session.query(Model).filter_by(model_job_id=data.get('eval_model_job_id')).first()
                data['model_id'] = model.id
        if data['global_config'] is not None:
            data['global_config'] = ParseDict(data['global_config'], ModelJobGlobalConfig())
        return data


# TODO(hangweiqiang): remove dataset_id in parameters
class ConfigModelJobParams(Schema):
    algorithm_id = fields.Integer(required=False, load_default=None)
    dataset_id = fields.Integer(required=False, load_default=None)
    config = fields.Dict(required=False, load_default=None)
    global_config = fields.Dict(required=False, load_default=None)
    comment = fields.Str(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        if data['config'] is not None:
            data['config'] = dict_to_workflow_definition(data['config'])
        if data['global_config'] is not None:
            data['global_config'] = ParseDict(data['global_config'], ModelJobGlobalConfig())
        return data


class ListModelJobsSchema(Schema):
    group_id = fields.Integer(required=False, load_default=None)
    keyword = fields.String(required=False, load_default=None)
    types = fields.List(fields.String(required=False,
                                      validate=validate.OneOf([
                                          ModelJobType.TRAINING.name, ModelJobType.EVALUATION.name,
                                          ModelJobType.PREDICTION.name
                                      ])),
                        required=False,
                        load_default=None)
    configured = fields.Boolean(required=False, load_default=None)
    algorithm_types = fields.List(fields.String(required=True,
                                                validate=validate.OneOf([
                                                    AlgorithmType.TREE_VERTICAL.name, AlgorithmType.NN_VERTICAL.name,
                                                    AlgorithmType.NN_HORIZONTAL.name
                                                ])),
                                  required=False,
                                  load_default=None)
    states = fields.List(fields.String(required=False,
                                       validate=validate.OneOf([s.name for s in WorkflowExternalState])),
                         required=False,
                         load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)
    filter_exp = FilterExpField(data_key='filter', required=False, load_default=None)
    sorter_exp = fields.String(required=False, load_default=None, data_key='order_by')

    @post_load()
    def make(self, data, **kwargs):
        if data['types'] is not None:
            data['types'] = [ModelJobType[t] for t in data['types']]
        if data['states'] is not None:
            data['states'] = [WorkflowExternalState[s] for s in data['states']]
        if data['algorithm_types'] is not None:
            data['algorithm_types'] = [AlgorithmType[t] for t in data['algorithm_types']]
        return data


class ModelJobApi(Resource):

    @credentials_required
    def get(self, project_id: int, model_job_id: int):
        """Get the model job by id
        ---
        tags:
          - mmgr
        description: get the model job by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobPb'
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            ModelJobService(session).update_model_job_status(model_job)
            ModelJobController(session, project_id).update_participants_auth_status(model_job)
            session.commit()
            return make_flask_response(model_job.to_proto())

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.UPDATE)
    @use_args(ConfigModelJobParams(), location='json')
    def put(self, params: dict, project_id: int, model_job_id: int):
        """Update the model job
        ---
        tags:
          - mmgr
        description: update the model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/ConfigModelJobParams'
        responses:
          200:
            description: detail of the model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobPb'
        """
        dataset_id = params['dataset_id']
        algorithm_id = params['algorithm_id']
        config = params['config']
        global_config = params['global_config']
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            model_job.algorithm_id = algorithm_id
            if dataset_id is not None:
                model_job.dataset_id = dataset_id
            model_job.comment = params['comment']
            if global_config is not None:
                configer = ModelJobConfiger(session=session,
                                            model_job_type=model_job.model_job_type,
                                            algorithm_type=model_job.algorithm_type,
                                            project_id=project_id)
                domain_name = SettingService.get_system_info().pure_domain_name
                config = configer.get_config(dataset_id=model_job.dataset_id,
                                             model_id=model_job.model_id,
                                             model_job_config=global_config.global_config[domain_name])
            ModelJobService(session).config_model_job(model_job, config=config, create_workflow=False)
            model_job.role = ModelJobRole.PARTICIPANT
            model_job.creator_username = get_current_user().username
            # Compatible with old versions, use PUT for authorization
            ModelJobService.update_model_job_auth_status(model_job=model_job, auth_status=AuthStatus.AUTHORIZED)
            ModelJobController(session, project_id).inform_auth_status_to_participants(model_job)

            session.commit()
            scheduler.wakeup(model_job.workflow_id)
            return make_flask_response(model_job.to_proto())

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.UPDATE)
    @use_kwargs(
        {
            'metric_is_public':
                fields.Boolean(required=False, load_default=None),
            'auth_status':
                fields.String(required=False, load_default=None, validate=validate.OneOf([s.name for s in AuthStatus])),
            'comment':
                fields.String(required=False, load_default=None)
        },
        location='json')
    def patch(self, project_id: int, model_job_id: int, metric_is_public: Optional[bool], auth_status: Optional[str],
              comment: Optional[str]):
        """Patch the attribute of model job
        ---
        tags:
          - mmgr
        description: change the attribuet of model job, e.g. whether metric is public
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  metric_is_public:
                    type: boolean
                  auth_status:
                    type: string
                  comment:
                    type: string
        responses:
          200:
            description: detail of the model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobPb'
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            if metric_is_public is not None:
                model_job.metric_is_public = metric_is_public
            if auth_status is not None:
                ModelJobService.update_model_job_auth_status(model_job=model_job, auth_status=AuthStatus[auth_status])
                ModelJobController(session, project_id).inform_auth_status_to_participants(model_job)
            model_job.creator_username = get_current_user().username
            if comment is not None:
                model_job.comment = comment
            session.commit()
            return make_flask_response(model_job.to_proto())

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.DELETE)
    def delete(self, project_id: int, model_job_id: int):
        """Delete the model job
        ---
        tags:
          - mmgr
        description: delete the model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        responses:
          204:
            description: delete the model job successfully
          409:
            description: model job cannot be deleted
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            if not model_job.is_deletable():
                raise ResourceConflictException(f'model job cannot be deleted due to model job is {model_job.state}')
            ModelJobService(session).delete(model_job.id)
            session.commit()
            return make_flask_response(status=HTTPStatus.NO_CONTENT)


class StartModelJobApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.UPDATE)
    def post(self, project_id: int, model_job_id: int):
        """Start the model job
        ---
        tags:
          - mmgr
        description: start the model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: start the model job successfully
        """
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(id=model_job_id, project_id=project_id).first()
            if model_job is None:
                raise NotFoundException(f'[StartModelJobApi] model job {model_job_id} is not found')
            start_model_job(model_job_id=model_job_id)
            return make_flask_response(status=HTTPStatus.OK)


class StopModelJobApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.UPDATE)
    def post(self, project_id: int, model_job_id: int):
        """Stop the model job
        ---
        tags:
          - mmgr
        description: stop the model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: stop the model job successfully
        """
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(id=model_job_id, project_id=project_id).first()
            if model_job is None:
                raise NotFoundException(f'[StopModelJobApi] model job {model_job_id} is not found')
            stop_model_job(model_job_id=model_job_id)
            return make_flask_response(status=HTTPStatus.OK)


class ModelJobMetricsApi(Resource):

    @credentials_required
    def get(self, project_id: int, model_job_id: int):
        """Get the model job metrics by id
        ---
        tags:
          - mmgr
        description: get the model job metrics by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the model job metrics
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobMetrics'
          500:
            description: error exists when query metrics for model job
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            try:
                metrics = ModelJobService(session).query_metrics(model_job)
            except ValueError as e:
                logging.warning(f'[Model]error when query metrics for model job {model_job_id}')
                raise InternalException(details=str(e)) from e
            return make_flask_response(metrics), HTTPStatus.OK


class ModelJobResultsApi(Resource):

    @credentials_required
    def get(self, project_id: int, model_job_id: int):
        """Get the model job result by id
        ---
        tags:
          - mmgr
        description: get the model job result by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_job_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: file of the model job results
            content:
              application/json:
                schema:
                  type: string
          204:
            description: the output path does not exist
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            output_path = model_job.get_output_path()
            file_manager = FileManager()
            if file_manager.exists(output_path):
                with tempfile.NamedTemporaryFile(suffix='.tar') as temp_file:
                    FileOperator().archive_to([output_path], temp_file.name)
                    return send_file(temp_file.name,
                                     attachment_filename=f'{model_job.name}_result.tar',
                                     mimetype='application/x-tar',
                                     as_attachment=True)
            return make_flask_response(status=HTTPStatus.NO_CONTENT)


def _validate_create_model_job_params(project_id: int,
                                      name: str,
                                      model_job_type: ModelJobType,
                                      model_id: int,
                                      group_id: Optional[int] = None):
    if model_job_type == ModelJobType.TRAINING and model_id is not None:
        raise InvalidArgumentException(details='model id must be None for training job')
    if model_job_type in [ModelJobType.EVALUATION, ModelJobType.PREDICTION] and model_id is None:
        raise InvalidArgumentException(details='model id must not be None for eval or predict job')
    if model_job_type == ModelJobType.TRAINING and group_id is None:
        raise InvalidArgumentException(details='training model job must be in a group')
    if model_job_type in [ModelJobType.EVALUATION, ModelJobType.PREDICTION] and group_id is not None:
        raise InvalidArgumentException(details='eval or predict job must not be in a group')
    with db.session_scope() as session:
        if group_id is not None:
            group = session.query(ModelJobGroup).filter_by(project_id=project_id, id=group_id).first()
            if group is None:
                raise InvalidArgumentException(f'group {group_id} is not found in project {project_id}')
        if model_id:
            model = session.query(Model).filter_by(project_id=project_id, id=model_id).first()
            if model is None:
                raise InvalidArgumentException(f'model {model_id} is not found in project {project_id}')
        model_job = session.query(ModelJob).filter_by(name=name).first()
        if model_job is not None:
            raise ResourceConflictException(f'model job {name} already exist')


def _build_model_job_configured_query(exp: SimpleExpression):
    if exp.bool_value:
        return Workflow.config.isnot(None)
    return Workflow.config.is_(None)


# TODO(hangweiqiang): use filtering expression
class ModelJobsApi(Resource):
    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'algorithm_type': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None}),
        'model_job_type': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None}),
        'configured': SupportedField(type=FieldType.BOOL, ops={FilterOp.EQUAL: _build_model_job_configured_query}),
        'role': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None}),
        'status': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None}),
        'auth_status': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None})
    }

    SORTER_FIELDS = ['created_at']

    def __init__(self):
        self._filter_builder = FilterBuilder(model_class=ModelJob, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = SorterBuilder(model_class=ModelJob, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_kwargs(ListModelJobsSchema(), location='query')
    def get(self, project_id: int, group_id: Optional[int], keyword: Optional[str], types: Optional[List[ModelJobType]],
            configured: Optional[bool], algorithm_types: Optional[List[AlgorithmType]],
            states: Optional[List[WorkflowExternalState]], page: Optional[int], page_size: Optional[int],
            filter_exp: Optional[FilterExpression], sorter_exp: str):
        """Get the list of model jobs
        ---
        tags:
          - mmgr
        description: get the list of model jobs
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: query
          name: group_id
          schema:
            type: integer
        - in: query
          name: keyword
          schema:
            type: string
        - in: query
          name: types
          schema:
            type: array
            items:
              type: string
        - in: query
          name: algorithm_types
          schema:
            type: array
            items:
              type: string
        - in: query
          name: states
          schema:
            type: array
            items:
              type: string
        - in: query
          name: configured
          schema:
            type: boolean
        - in: query
          name: filter
          schema:
            type: string
        - in: query
          name: order_by
          schema:
            type: string
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        responses:
          200:
            description: list of model jobs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobRef'
        """
        # update auth_status and participants_info of old data
        with db.session_scope() as session:
            model_jobs = session.query(ModelJob).filter_by(participants_info=None, project_id=project_id).all()
            if model_jobs is not None:
                participants = ParticipantService(session).get_participants_by_project(project_id)
                participants_info = ParticipantsInfo(participants_map={
                    p.pure_domain_name(): ParticipantInfo(auth_status=AuthStatus.AUTHORIZED.name) for p in participants
                })
                pure_domain_name = SettingService.get_system_info().pure_domain_name
                participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.AUTHORIZED.name
                for model_job in model_jobs:
                    model_job.auth_status = AuthStatus.AUTHORIZED
                    model_job.set_participants_info(participants_info)
            session.commit()
        with db.session_scope() as session:
            query = session.query(ModelJob)
            if project_id:
                query = query.filter_by(project_id=project_id)
            if group_id is not None:
                query = query.filter_by(group_id=group_id)
            if types is not None:
                query = query.filter(ModelJob.model_job_type.in_(types))
            if algorithm_types is not None:
                query = query.filter(ModelJob.algorithm_type.in_(algorithm_types))
            if keyword is not None:
                query = query.filter(ModelJob.name.like(f'%{keyword}%'))
            if configured is not None:
                if configured:
                    query = query.join(ModelJob.workflow).filter(Workflow.config.isnot(None))
                else:
                    query = query.join(ModelJob.workflow).filter(Workflow.config.is_(None))
            if filter_exp:
                try:
                    query = query.outerjoin(Workflow, Workflow.uuid == ModelJob.workflow_uuid)
                    query = self._filter_builder.build_query(query, filter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            try:
                if sorter_exp is not None:
                    sorter_exp = parse_expression(sorter_exp)
                else:
                    sorter_exp = SortExpression(field='created_at', is_asc=False)
                query = self._sorter_builder.build_query(query, sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
            pagination = paginate(query, page, page_size)
            model_jobs = pagination.get_items()
            for model_job in model_jobs:
                ModelJobService(session).update_model_job_status(model_job)
            if states is not None:
                model_jobs = [m for m in model_jobs if m.state in states]
            data = [m.to_ref() for m in model_jobs]
            session.commit()
            return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.CREATE)
    @use_args(CreateModelJobParams(), location='json')
    def post(self, params: dict, project_id: int):
        """Create a model job
        ---
        tags:
          - mmgr
        description: create a model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/CreateModelJobParams'
        responses:
          201:
            description: detail of the model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobPb'
          500:
            description: error exists when creating model job
        """
        name = params['name']
        config = params['config']
        model_job_type = params['model_job_type']
        algorithm_type = params['algorithm_type']
        model_id = params['model_id']
        group_id = params['group_id']
        dataset_id = params['dataset_id']
        data_batch_id = params['data_batch_id']
        algorithm_id = params['algorithm_id']
        global_config = params['global_config']
        comment = params['comment']
        with db.session_scope() as session:
            get_project(project_id, session)
        _validate_create_model_job_params(project_id, name, model_job_type, model_id, group_id)
        # if platform is old version or the peer's platform is old version
        if not global_config or not _check_model_job_global_config_enable(project_id):
            if data_batch_id is not None:
                raise InternalException('auto update is not supported when our\'s or peer\'s platform is old version')
            # model job type is TRAINING
            if model_job_type in [ModelJobType.TRAINING]:
                with db.session_scope() as session:
                    model_job = ModelJobController(session, project_id).launch_model_job(group_id=group_id)
                    session.commit()
                    return make_flask_response(model_job.to_proto(), status=HTTPStatus.CREATED)
            # model job type is EVALUATION or PREDICTION
            pure_domain_name = SettingService.get_system_info().pure_domain_name
            succeeded, msg = CreateModelJob().run(project_id=project_id,
                                                  name=name,
                                                  model_job_type=model_job_type,
                                                  coordinator_pure_domain_name=pure_domain_name,
                                                  algorithm_type=algorithm_type,
                                                  dataset_id=dataset_id,
                                                  model_id=model_id,
                                                  group_id=group_id)
            if not succeeded:
                raise InternalException(f'error when creating model job with message: {msg}')
            with db.session_scope() as session:
                model_job: ModelJob = session.query(ModelJob).filter_by(name=name).first()
                model_job.algorithm_id = algorithm_id
                model_job.comment = comment
                model_job.creator_username = get_current_user().username
                workflow_uuid = model_job.workflow_uuid
                ModelJobService(session).config_model_job(model_job=model_job,
                                                          config=config,
                                                          create_workflow=True,
                                                          workflow_uuid=workflow_uuid)
                model_job.role = ModelJobRole.COORDINATOR
                session.commit()
                workflow = session.query(Workflow).filter_by(uuid=workflow_uuid).first()
                # TODO(gezhengqiang): refactor config_model_job service and remove wake up after refactoring workflow
                scheduler.wakeup(workflow.id)
                return make_flask_response(data=model_job.to_proto(), status=HTTPStatus.CREATED)
        # new version
        with db.session_scope() as session:
            version = None
            # model job type is TRAINING
            if group_id:
                group: ModelJobGroup = ModelJobGroupService(session).lock_and_update_version(group_id)
                if group.get_group_auth_frontend_status() not in [GroupAuthFrontendStatus.ALL_AUTHORIZED]:
                    raise UnauthorizedException(f'participants not all authorized in the group {group.name}')
                version = group.latest_version
            model_job = ModelJobService(session).create_model_job(name=name,
                                                                  uuid=resource_uuid(),
                                                                  role=ModelJobRole.COORDINATOR,
                                                                  model_job_type=model_job_type,
                                                                  algorithm_type=algorithm_type,
                                                                  global_config=global_config,
                                                                  group_id=group_id,
                                                                  project_id=project_id,
                                                                  data_batch_id=data_batch_id,
                                                                  comment=comment,
                                                                  version=version)
            model_job.creator_username = get_current_user().username
            if group_id and data_batch_id is not None:
                group.auto_update_status = GroupAutoUpdateStatus.ACTIVE
                group.start_data_batch_id = data_batch_id
                ModelJobGroupController(session=session, project_id=project_id).update_participants_model_job_group(
                    uuid=group.uuid,
                    auto_update_status=group.auto_update_status,
                    start_data_batch_id=group.start_data_batch_id)
            session.commit()
            return make_flask_response(data=model_job.to_proto(), status=HTTPStatus.CREATED)


class PeerModelJobApi(Resource):

    @credentials_required
    def get(self, project_id: int, model_job_id: int, participant_id: int):
        """Get the peer model job
        ---
        tags:
          - mmgr
        description: get the peer model job
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
        - in: path
          name: model_job_id
          required: true
          schema:
            type: integer
        - in: path
          name: participant_id
          required: true
          schema:
            type: integer
        responses:
          200:
            description: get the peer model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.PeerModelJobPb'
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            project = model_job.project
            participant = get_participant(participant_id, project)
            client = RpcClient.from_project_and_participant(project.name, project.token, participant.domain_name)
            resp = client.get_model_job(model_job_uuid=model_job.uuid, need_metrics=False)
            # to support backward compatibility, since peer system may not have metric_is_public
            # TODO(hangweiqiang): remove code of backward compatibility
            metric_is_public = True
            if resp.HasField('metric_is_public'):
                metric_is_public = resp.metric_is_public.value
            peer_job = PeerModelJobPb(name=resp.name,
                                      uuid=resp.uuid,
                                      algorithm_type=resp.algorithm_type,
                                      model_job_type=resp.model_job_type,
                                      state=resp.state,
                                      group_uuid=resp.group_uuid,
                                      config=resp.config,
                                      metric_is_public=metric_is_public)
        return make_flask_response(peer_job, status=HTTPStatus.OK)


class PeerModelJobMetricsApi(Resource):

    @credentials_required
    def get(self, project_id: int, model_job_id: int, participant_id: int):
        """Get the peer model job metrics
        ---
        tags:
          - mmgr
        description: get the peer model job metrics
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
        - in: path
          name: model_job_id
          required: true
          schema:
            type: integer
        - in: path
          name: participant_id
          required: true
          schema:
            type: integer
        responses:
          200:
            description: detail of the model job metrics
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobMetrics'
          403:
            description: the metric of peer model job is not public
        """
        with db.session_scope() as session:
            model_job = get_model_job(project_id, model_job_id, session)
            project = model_job.project
            participant = get_participant(participant_id, project)
            client = RpcClient.from_project_and_participant(project.name, project.token, participant.domain_name)
            resp = client.get_model_job(model_job_uuid=model_job.uuid, need_metrics=True)
            if resp.HasField('metric_is_public') and not resp.metric_is_public.value:
                raise NoAccessException('peer metric is not public')
            metrics = json.loads(resp.metrics)
        return make_flask_response(metrics, status=HTTPStatus.OK)


class LaunchModelJobApi(Resource):

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB, op_type=Event.OperationType.CREATE)
    def post(self, project_id: int, group_id: int):
        """Launch the model job
        ---
        tags:
          - mmgr
        description: launch the model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: group_id
          schema:
            type: integer
          required: true
        responses:
          201:
            description: launch the model job successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobPb'
          500:
            description: error exists when launching model job by 2PC
        """
        with db.session_scope() as session:
            model_job = ModelJobController(session, project_id).launch_model_job(group_id=group_id)
            return make_flask_response(model_job.to_proto(), status=HTTPStatus.CREATED)


class NextAutoUpdateModelJobApi(Resource):

    @credentials_required
    def get(self, project_id: int, group_id: int):
        """Get the next auto update model job
        ---
        tags:
          - mmgr
        description: get the next auto update model job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: group_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobPb'
        """
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(project_id=project_id, group_id=group_id,
                                                          auto_update=True).order_by(
                                                              ModelJob.created_at.desc()).limit(1).first()
            if model_job is None:
                group = session.query(ModelJobGroup).get(group_id)
                raise NotFoundException(f'The auto update model job update the group {group.name} is not found')
            if model_job.status in [ModelJobStatus.CONFIGURED, ModelJobStatus.RUNNING, ModelJobStatus.PENDING]:
                raise InternalException(f'The latest auto update model job {model_job.name} is running')
            data_batch_id = 0
            load_model_name = ''
            if model_job.status in [ModelJobStatus.STOPPED, ModelJobStatus.FAILED, ModelJobStatus.ERROR]:
                previous_success_model_job = session.query(ModelJob).filter_by(
                    project_id=project_id, group_id=group_id, auto_update=True,
                    status=ModelJobStatus.SUCCEEDED).order_by(ModelJob.created_at.desc()).limit(1).first()
                if previous_success_model_job is None:
                    return make_flask_response(model_job.to_proto())
                model_job = previous_success_model_job
            next_data_batch = BatchService(session).get_next_batch(model_job.data_batch)
            if model_job.status in [ModelJobStatus.SUCCEEDED] and next_data_batch is not None:
                model = session.query(Model).filter_by(model_job_id=model_job.id).first()
                if model is None:
                    raise NotFoundException(f'The model job {model_job.name}\'s model is not found')
                load_model_name = model.name
                data_batch_id = next_data_batch.id
                if model_job.model_id is None:
                    model_job.model_id = model.id
            model_job.data_batch_id = data_batch_id
            global_config = model_job.get_global_config()
            if global_config is not None:
                for config in global_config.global_config.values():
                    set_load_model_name(config, load_model_name)
            model_job.set_global_config(global_config)
            return make_flask_response(model_job.to_proto())


class ModelJobDefinitionApi(Resource):

    @credentials_required
    @use_kwargs(
        {
            'model_job_type': fields.Str(required=True, validate=validate.OneOf([t.name for t in ModelJobType])),
            'algorithm_type': fields.Str(required=True, validate=validate.OneOf([t.name for t in AlgorithmType])),
        },
        location='query')
    def get(self, model_job_type: str, algorithm_type: str):
        """Get variables of model_job
        ---
        tags:
          - mmgr
        description: Get variables of given type of algorithm and model job
        parameters:
        - in: path
          name: model_job_type
          schema:
            type: string
        - in: path
          name: algorithm_type
          schema:
            type: string
        responses:
          200:
            description: variables of given algorithm type and model job type
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    variables:
                      type: array
                      items:
                        $ref: '#/definitions/fedlearner_webconsole.proto.Variable'
                    is_federated:
                      type: boolean
        """
        model_job_type = ModelJobType[model_job_type]
        algorithm_type = AlgorithmType[algorithm_type]
        with db.session_scope() as session:
            template_id = get_sys_template_id(session=session,
                                              algorithm_type=algorithm_type,
                                              model_job_type=model_job_type)
            template: WorkflowTemplate = session.query(WorkflowTemplate).get(template_id)
            config = template.get_config()
            variables = config.job_definitions[0].variables
            flag = is_federated(algorithm_type=algorithm_type, model_job_type=model_job_type)
            return make_flask_response(data={'variables': list(variables), 'is_federated': flag})


def initialize_mmgr_model_job_apis(api):
    api.add_resource(ModelJobsApi, '/projects/<int:project_id>/model_jobs')
    api.add_resource(ModelJobApi, '/projects/<int:project_id>/model_jobs/<int:model_job_id>')
    api.add_resource(ModelJobMetricsApi, '/projects/<int:project_id>/model_jobs/<int:model_job_id>/metrics')
    api.add_resource(ModelJobResultsApi, '/projects/<int:project_id>/model_jobs/<int:model_job_id>/results')
    api.add_resource(StartModelJobApi, '/projects/<int:project_id>/model_jobs/<int:model_job_id>:start')
    api.add_resource(StopModelJobApi, '/projects/<int:project_id>/model_jobs/<int:model_job_id>:stop')
    api.add_resource(PeerModelJobApi,
                     '/projects/<int:project_id>/model_jobs/<int:model_job_id>/peers/<int:participant_id>')
    api.add_resource(PeerModelJobMetricsApi,
                     '/projects/<int:project_id>/model_jobs/<int:model_job_id>/peers/<int:participant_id>/metrics')
    api.add_resource(LaunchModelJobApi, '/projects/<int:project_id>/model_job_groups/<int:group_id>:launch')
    api.add_resource(NextAutoUpdateModelJobApi,
                     '/projects/<int:project_id>/model_job_groups/<int:group_id>/next_auto_update_model_job')
    api.add_resource(ModelJobDefinitionApi, '/model_job_definitions')

    schema_manager.append(CreateModelJobParams)
    schema_manager.append(ConfigModelJobParams)
    schema_manager.append(ListModelJobsSchema)
