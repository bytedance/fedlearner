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

from http import HTTPStatus
from flask_restful import Resource
from typing import Optional
from webargs.flaskparser import use_args, use_kwargs
from marshmallow import Schema, post_load, fields, validate
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import ResourceConflictException, InternalException, InvalidArgumentException
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp, SimpleExpression
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.mmgr_pb2 import ModelJobGlobalConfig, AlgorithmProjectList
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.proto.review_pb2 import TicketDetails, TicketType
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.utils.sorting import SorterBuilder, SortExpression, parse_expression
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.workflow_template.service import dict_to_workflow_definition
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.mmgr.controller import CreateModelJobGroup, ModelJobGroupController
from fedlearner_webconsole.mmgr.models import ModelJobGroup, ModelJobType, ModelJobRole, GroupCreateStatus, \
    GroupAutoUpdateStatus
from fedlearner_webconsole.mmgr.service import ModelJobGroupService, get_model_job_group, get_participant,\
    get_dataset, get_project, get_algorithm, ModelJobService
from fedlearner_webconsole.mmgr.model_job_configer import ModelJobConfiger
from fedlearner_webconsole.algorithm.models import AlgorithmType, AlgorithmProject
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator
from fedlearner_webconsole.utils.flask_utils import FilterExpField, make_flask_response, get_current_user
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.swagger.models import schema_manager


class CreateModelJobGroupParams(Schema):
    name = fields.Str(required=True)
    dataset_id = fields.Integer(required=False, load_default=None)
    algorithm_type = fields.Str(required=True,
                                validate=validate.OneOf([
                                    AlgorithmType.TREE_VERTICAL.name, AlgorithmType.NN_VERTICAL.name,
                                    AlgorithmType.NN_HORIZONTAL.name
                                ]))

    @post_load()
    def make(self, data, **kwargs):
        data['algorithm_type'] = AlgorithmType[data['algorithm_type']]
        return data


class CreateModelJobGroupParamsV2(Schema):
    name = fields.Str(required=True)
    dataset_id = fields.Integer(required=True)
    algorithm_type = fields.Str(required=True,
                                validate=validate.OneOf([
                                    AlgorithmType.TREE_VERTICAL.name, AlgorithmType.NN_VERTICAL.name,
                                    AlgorithmType.NN_HORIZONTAL.name
                                ]))
    algorithm_project_list = fields.Dict(required=False, load_default=None)
    comment = fields.Str(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['algorithm_type'] = AlgorithmType[data['algorithm_type']]
        if data['algorithm_project_list'] is not None:
            data['algorithm_project_list'] = ParseDict(data['algorithm_project_list'], AlgorithmProjectList())
        return data


class ConfigModelJobGroupParams(Schema):
    authorized = fields.Boolean(required=False, load_default=None)
    algorithm_id = fields.Integer(required=False, load_default=None)
    config = fields.Dict(required=False, load_default=None)
    cron_config = fields.String(required=False, load_default=None)
    comment = fields.Str(required=False, load_default=None)
    # TODO(gezhengqiang): delete dataset_id
    dataset_id = fields.Integer(required=False, load_default=None)
    global_config = fields.Dict(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        if data['config'] is not None:
            data['config'] = dict_to_workflow_definition(data['config'])
        if data['global_config'] is not None:
            data['global_config'] = ParseDict(data['global_config'], ModelJobGlobalConfig())
        return data


class ConfigPeerModelJobGroup(Schema):
    config = fields.Dict(required=False, load_default=None)
    global_config = fields.Dict(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        if data['config'] is None and data['global_config'] is None:
            raise InvalidArgumentException('either config or global config must be set')
        if data['config'] is not None:
            data['config'] = dict_to_workflow_definition(data['config'])
        if data['global_config'] is not None:
            data['global_config'] = ParseDict(data['global_config'], ModelJobGlobalConfig())
        return data


def _build_group_configured_query(exp: SimpleExpression):
    if exp.bool_value:
        return ModelJobGroup.config.isnot(None)
    return ModelJobGroup.config.is_(None)


class ModelJobGroupsApi(Resource):

    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'configured': SupportedField(
            type=FieldType.BOOL,
            ops={
                FilterOp.EQUAL: _build_group_configured_query,
            },
        ),
        'role': SupportedField(type=FieldType.STRING, ops={
            FilterOp.IN: None,
        }),
        'algorithm_type': SupportedField(type=FieldType.STRING, ops={
            FilterOp.IN: None,
        }),
    }

    SORTER_FIELDS = ['created_at']

    def __init__(self):
        self._filter_builder = FilterBuilder(model_class=ModelJobGroup, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = SorterBuilder(model_class=ModelJobGroup, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_kwargs(
        {
            'page': fields.Integer(required=False, load_default=None),
            'page_size': fields.Integer(required=False, load_default=None),
            'filter_exp': FilterExpField(data_key='filter', required=False, load_default=None),
            'sorter_exp': fields.String(required=False, load_default=None, data_key='order_by'),
        },
        location='query')
    def get(
        self,
        page: Optional[int],
        page_size: Optional[int],
        filter_exp: Optional[FilterExpression],
        sorter_exp: Optional[str],
        project_id: int,
    ):
        """Get the list of model job groups
        ---
        tags:
          - mmgr
        description: get the list of model job groups
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: filter
          schema:
            type: string
        responses:
          200:
            description: the list of model job groups
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobGroupRef'
        """
        with db.session_scope() as session:
            # to filter out groups created by old api determined by uuid
            query = session.query(ModelJobGroup).filter(ModelJobGroup.uuid.isnot(None))
            if project_id:
                query = query.filter_by(project_id=project_id)
            if filter_exp:
                try:
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
            for group in pagination.get_items():
                if len(group.model_jobs) != 0:
                    ModelJobService(session).update_model_job_status(group.model_jobs[0])
            data = [d.to_ref() for d in pagination.get_items()]
            session.commit()
            return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP, op_type=Event.OperationType.CREATE)
    @use_args(CreateModelJobGroupParams(), location='json')
    def post(self, params: dict, project_id: int):
        """Create the model job group
        ---
        tags:
          - mmgr
        description: create the model job group
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
                $ref: '#/definitions/CreateModelJobGroupParams'
        responses:
          201:
            description: the detail of the model job group
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobGroupPb'
          409:
            description: the group already exists
          500:
            description: error exists when creating model job by 2PC
        """
        name = params['name']
        dataset_id = params['dataset_id']
        with db.session_scope() as session:
            get_project(project_id, session)
            if dataset_id:
                get_dataset(dataset_id, session)
            group = session.query(ModelJobGroup).filter_by(name=name).first()
            if group is not None:
                raise ResourceConflictException(f'group {name} already exists')
            pure_domain_name = SettingService.get_system_info().pure_domain_name
            model_job_group_uuid = resource_uuid()
            group = ModelJobGroup(name=name,
                                  uuid=model_job_group_uuid,
                                  project_id=project_id,
                                  dataset_id=dataset_id,
                                  algorithm_type=params['algorithm_type'],
                                  role=ModelJobRole.COORDINATOR,
                                  creator_username=get_current_user().username,
                                  authorized=True,
                                  auth_status=AuthStatus.AUTHORIZED)
            participants = ParticipantService(session).get_participants_by_project(project_id)
            participants_info = ParticipantsInfo(participants_map={
                p.pure_domain_name(): ParticipantInfo(auth_status=AuthStatus.PENDING.name) for p in participants
            })
            participants_info.participants_map[pure_domain_name].auth_status = AuthStatus.AUTHORIZED.name
            group.set_participants_info(participants_info)
            session.add(group)
            ticket_helper = get_ticket_helper(session)
            ticket_helper.create_ticket(TicketType.CREATE_MODELJOB_GROUP, TicketDetails(uuid=group.uuid))
            session.commit()
        succeeded, msg = CreateModelJobGroup().run(project_id=project_id,
                                                   name=name,
                                                   algorithm_type=params['algorithm_type'],
                                                   dataset_id=dataset_id,
                                                   coordinator_pure_domain_name=pure_domain_name,
                                                   model_job_group_uuid=model_job_group_uuid)
        if not succeeded:
            raise InternalException(f'creating model job by 2PC with message: {msg}')
        with db.session_scope() as session:
            group: ModelJobGroup = session.query(ModelJobGroup).filter_by(name=name).first()
            group.status = GroupCreateStatus.SUCCEEDED
            session.commit()
            return make_flask_response(data=group.to_proto(), status=HTTPStatus.CREATED)


class ModelJobGroupsApiV2(Resource):

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP, op_type=Event.OperationType.CREATE)
    @use_args(CreateModelJobGroupParamsV2(), location='json')
    def post(self, params: dict, project_id: int):
        """Create the model job group
        ---
        tags:
          - mmgr
        description: create the model job group
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
                $ref: '#/definitions/CreateModelJobGroupParamsV2'
        responses:
          201:
            description: the detail of the model job group
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobGroupPb'
          409:
            description: the group already exists
        """
        name = params['name']
        dataset_id = params['dataset_id']
        algorithm_type = params['algorithm_type']
        algorithm_project_list = AlgorithmProjectList()
        if params['algorithm_project_list']:
            algorithm_project_list = params['algorithm_project_list']
        with db.session_scope() as session:
            get_project(project_id, session)
            get_dataset(dataset_id, session)
            group = session.query(ModelJobGroup).filter_by(name=name).first()
            if group is not None:
                raise ResourceConflictException(f'group {name} already exists')
            model_job_group_uuid = resource_uuid()
            group = ModelJobGroup(name=name,
                                  uuid=model_job_group_uuid,
                                  project_id=project_id,
                                  dataset_id=dataset_id,
                                  algorithm_type=algorithm_type,
                                  role=ModelJobRole.COORDINATOR,
                                  creator_username=get_current_user().username,
                                  comment=params['comment'])
            # make configured true
            group.set_config()
            pure_domain_name = SettingService.get_system_info().pure_domain_name
            # set algorithm project uuid map
            group.set_algorithm_project_uuid_list(algorithm_project_list)
            # set algorithm project id
            algorithm_project_uuid = algorithm_project_list.algorithm_projects.get(pure_domain_name)
            if algorithm_project_uuid is None and algorithm_type not in [AlgorithmType.TREE_VERTICAL]:
                raise Exception(f'algorithm project uuid must be given if algorithm type is {algorithm_type.name}')
            if algorithm_project_uuid is not None:
                algorithm_project = session.query(AlgorithmProject).filter_by(uuid=algorithm_project_uuid).first()
                if algorithm_project is not None:
                    group.algorithm_project_id = algorithm_project.id
            session.add(group)
            ModelJobGroupService(session).initialize_auth_status(group)
            ticket_helper = get_ticket_helper(session)
            ticket_helper.create_ticket(TicketType.CREATE_MODELJOB_GROUP, TicketDetails(uuid=group.uuid))
            if group.ticket_status in [TicketStatus.APPROVED]:
                ModelJobGroupController(
                    session=session,
                    project_id=project_id).create_model_job_group_for_participants(model_job_group_id=group.id)
            session.commit()
            return make_flask_response(group.to_proto(), status=HTTPStatus.CREATED)


class ModelJobGroupApi(Resource):

    @credentials_required
    def get(self, project_id: int, group_id: int):
        """Get the model job group
        ---
        tags:
          - mmgr
        descriptions: get the model job group
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
            description: detail of the model job group
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobGroupPb'
        """
        with db.session_scope() as session:
            group = get_model_job_group(project_id=project_id, group_id=group_id, session=session)
            ModelJobGroupController(session, project_id).update_participants_auth_status(group)
            return make_flask_response(group.to_proto())

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP, op_type=Event.OperationType.UPDATE)
    @use_args(ConfigModelJobGroupParams(), location='json')
    def put(self, params: dict, project_id: int, group_id: int):
        """Update the model job group
        ---
        tags:
          - mmgr
        description: update the model job group
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
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/ConfigModelJobGroupParams'
        responses:
          200:
            description: update the model job group successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobGroupPb'
          400:
            description: algorihm is not found or algorithm type mismatch between group and algorithms
        """
        with db.session_scope() as session:
            group = get_model_job_group(project_id=project_id, group_id=group_id, session=session)
            if params['authorized'] is not None:
                group.authorized = params['authorized']
                if group.authorized:
                    group.auth_status = AuthStatus.AUTHORIZED
                    group.set_config()
                else:
                    group.auth_status = AuthStatus.PENDING
                ModelJobGroupController(session, project_id).inform_auth_status_to_participants(group)
            if params['algorithm_id'] is not None:
                algorithm = get_algorithm(project_id=project_id, algorithm_id=params['algorithm_id'], session=session)
                if algorithm is None:
                    raise InvalidArgumentException(f'algorithm {params["algorithm_id"]} is not found')
                if algorithm.type != group.algorithm_type:
                    raise InvalidArgumentException(f'algorithm type mismatch between group and algorithm: '
                                                   f'{group.algorithm_type.name} vs {algorithm.type.name}')
                group.algorithm_id = params['algorithm_id']
                group.algorithm_project_id = algorithm.algorithm_project_id
            if params['dataset_id'] is not None:
                group.dataset_id = params['dataset_id']
            if params['config'] is not None:
                configer = ModelJobConfiger(session=session,
                                            model_job_type=ModelJobType.TRAINING,
                                            algorithm_type=group.algorithm_type,
                                            project_id=project_id)
                configer.set_dataset(config=params['config'], dataset_id=group.dataset_id)
                group.set_config(params['config'])
            if params['global_config'] is not None:
                configer = ModelJobConfiger(session=session,
                                            model_job_type=ModelJobType.TRAINING,
                                            algorithm_type=group.algorithm_type,
                                            project_id=project_id)
                domain_name = SettingService.get_system_info().pure_domain_name
                config = configer.get_config(dataset_id=group.dataset_id,
                                             model_id=None,
                                             model_job_config=params['global_config'].global_config[domain_name])
                group.set_config(config)
            if params['comment'] is not None:
                group.comment = params['comment']
            if group.creator_username is None:
                group.creator_username = get_current_user().username
            if params['cron_config'] is not None:
                ModelJobGroupService(session).update_cronjob_config(group=group, cron_config=params['cron_config'])
            session.commit()
            return make_flask_response(data=group.to_proto())

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP, op_type=Event.OperationType.DELETE)
    def delete(self, project_id: int, group_id: int):
        """Delete the model job group
        ---
        tags:
          - mmgr
        description: delete the model job group
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
          204:
            description: delete the model job group successfully
          409:
            description: group cannot be deleted due to some model job is ready or running
        """
        with db.session_scope() as session:
            group = get_model_job_group(project_id=project_id, group_id=group_id, session=session)
            if not group.is_deletable():
                raise ResourceConflictException('group cannot be deleted due to some model job is ready or running')
            ModelJobGroupService(session).delete(group.id)
            session.commit()
            return make_flask_response(status=HTTPStatus.NO_CONTENT)


class PeerModelJobGroupApi(Resource):

    @credentials_required
    def get(self, project_id: int, group_id: int, participant_id: int):
        """Get the peer model job group
        ---
        tags:
          - mmgr
        description: Get the peer model job group
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
        - in: path
          name: participant_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the model job group
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.GetModelJobGroupResponse'
        """
        with db.session_scope() as session:
            group = get_model_job_group(project_id=project_id, group_id=group_id, session=session)
            resp = ModelJobGroupController(session, project_id).get_model_job_group_from_participant(
                participant_id=participant_id, model_job_group_uuid=group.uuid)
        return make_flask_response(resp, status=HTTPStatus.OK)

    @credentials_required
    @use_args(ConfigPeerModelJobGroup(), location='json')
    def patch(self, params: dict, project_id: int, group_id: int, participant_id: int):
        """Patch a peer model job group
        ---
        tags:
          - mmgr
        description: patch a peer model job group
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
        - in: path
          name: participant_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/ConfigPeerModelJobGroup'
        responses:
          200:
            description: update the peer model job group successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.UpdateModelJobGroupResponse'
        """
        config = params['config']
        global_config = params['global_config']
        with db.session_scope() as session:
            group = get_model_job_group(project_id=project_id, group_id=group_id, session=session)
            project = group.project
            participant = get_participant(participant_id, project)
            client = RpcClient.from_project_and_participant(project.name, project.token, participant.domain_name)
            if global_config is not None:
                configer = ModelJobConfiger(session=session,
                                            model_job_type=ModelJobType.TRAINING,
                                            algorithm_type=group.algorithm_type,
                                            project_id=project_id)
                domain_name = participant.pure_domain_name()
                config = configer.get_config(dataset_id=group.dataset_id,
                                             model_id=None,
                                             model_job_config=global_config.global_config[domain_name])
            resp = client.update_model_job_group(model_job_group_uuid=group.uuid, config=config)
        return make_flask_response(resp, status=HTTPStatus.OK)


class ModelJobGroupStopAutoUpdateApi(Resource):

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL_JOB_GROUP, op_type=Event.OperationType.STOP)
    def post(self, project_id: int, group_id: int):
        """Stop trigger auto update model job in this model job group
        ---
        tags:
          - mmgr
        description: create the model job group
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
            description: stop the auto update model job successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelJobGroupPb'
        """
        with db.session_scope() as session:
            group: ModelJobGroup = get_model_job_group(project_id=project_id, group_id=group_id, session=session)
            group.auto_update_status = GroupAutoUpdateStatus.STOPPED
            ModelJobGroupController(session=session, project_id=project_id).update_participants_model_job_group(
                uuid=group.uuid, auto_update_status=group.auto_update_status)
            session.commit()
            return make_flask_response(data=group.to_proto(), status=HTTPStatus.OK)


def initialize_mmgr_model_job_group_apis(api):
    api.add_resource(ModelJobGroupsApi, '/projects/<int:project_id>/model_job_groups')
    api.add_resource(ModelJobGroupsApiV2, '/projects/<int:project_id>/model_job_groups_v2')
    api.add_resource(ModelJobGroupApi, '/projects/<int:project_id>/model_job_groups/<int:group_id>')
    api.add_resource(ModelJobGroupStopAutoUpdateApi,
                     '/projects/<int:project_id>/model_job_groups/<int:group_id>:stop_auto_update')
    api.add_resource(PeerModelJobGroupApi,
                     '/projects/<int:project_id>/model_job_groups/<int:group_id>/peers/<int:participant_id>')

    schema_manager.append(CreateModelJobGroupParams)
    schema_manager.append(CreateModelJobGroupParamsV2)
    schema_manager.append(ConfigModelJobGroupParams)
    schema_manager.append(ConfigPeerModelJobGroup)
