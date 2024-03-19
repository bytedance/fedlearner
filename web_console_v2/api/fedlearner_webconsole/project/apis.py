# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from enum import Enum
from functools import partial
from http import HTTPStatus
from typing import Optional, Dict, Any, List

from google.protobuf.json_format import ParseDict
from flask_restful import Resource, Api
from marshmallow import Schema, fields, validate, post_load
from marshmallow.validate import Length

from envs import Envs
from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.db import db
from fedlearner_webconsole.iam.client import create_iams_for_resource
from fedlearner_webconsole.iam.iam_required import iam_required
from fedlearner_webconsole.iam.permission import Permission
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.participant.models import ProjectParticipant
from fedlearner_webconsole.project.controllers import PendingProjectRpcController
from fedlearner_webconsole.project.models import Project, PendingProjectState, ProjectRole, PendingProject
from fedlearner_webconsole.project.services import ProjectService, PendingProjectService
from fedlearner_webconsole.proto.common_pb2 import StatusCode, Variable
from fedlearner_webconsole.exceptions \
    import InvalidArgumentException, NotFoundException, ResourceConflictException, InternalException
from fedlearner_webconsole.proto.project_pb2 import ProjectConfig
from fedlearner_webconsole.proto.review_pb2 import TicketType, TicketDetails
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.rpc.v2.project_service_client import ProjectServiceClient
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator, use_args, use_kwargs
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.flask_utils import get_current_user, make_flask_response, FilterExpField


class ErrorMessage(Enum):
    PARAM_FORMAT_ERROR = 'Format of parameter {} is wrong: {}'


def _add_variable(config: Optional[Dict], field: str, value: Any) -> Dict:
    config = config or {}
    config['variables'] = config.get('variables', [])
    for item in config['variables']:
        if item['name'] == field:
            return config
    config['variables'].append({'name': field, 'value': value})
    return config


class CreateProjectParameter(Schema):
    name = fields.String(required=True)
    config = fields.Dict(load_default={})
    # System does not support multiple participants now
    participant_ids = fields.List(fields.Integer(), validate=Length(equal=1))
    comment = fields.String(load_default='')


class CreatePendingProjectParameter(Schema):
    name = fields.String(required=True)
    config = fields.Dict(load_default={})
    participant_ids = fields.List(fields.Integer(), validate=Length(min=1))
    comment = fields.String(load_default='')

    @post_load()
    def make(self, data, **kwargs):
        data['config'] = ParseDict(data['config'], ProjectConfig(), ignore_unknown_fields=True)
        return data


class ProjectsApi(Resource):

    @input_validator
    @credentials_required
    @iam_required(Permission.PROJECTS_POST)
    @emits_event(audit_fields=['participant_ids'])
    @use_args(CreateProjectParameter())
    def post(self, data: Dict):
        """Creates a new project.
        ---
        tags:
          - project
        description: Creates a new project
        parameters:
        - in: body
          name: body
          schema:
            $ref: '#/definitions/CreateProjectParameter'
        responses:
          201:
            description: Created a project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Project'
        """
        name = data['name']
        config = data['config']
        comment = data['comment']
        participant_ids = data['participant_ids']
        with db.session_scope() as session:
            if session.query(Project).filter_by(name=name).first() is not None:
                raise ResourceConflictException(message=f'Project name {name} has been used.')

        with db.session_scope() as session:
            try:
                user = get_current_user()
                # defensive programming, if user is none, wont query user.username
                new_project = Project(name=name, comment=comment, creator=user and user.username)
                config = _add_variable(config, 'storage_root_path', Envs.STORAGE_ROOT)
                try:
                    new_project.set_config(ParseDict(config, ProjectConfig()))
                except Exception as e:
                    raise InvalidArgumentException(
                        details=ErrorMessage.PARAM_FORMAT_ERROR.value.format('config', e)) from e
                session.add(new_project)
                session.flush()

                for participant_id in participant_ids:
                    # insert a relationship into the table
                    new_relationship = ProjectParticipant(project_id=new_project.id, participant_id=participant_id)
                    session.add(new_relationship)

                create_iams_for_resource(new_project, user)
                session.commit()
            except Exception as e:
                raise InvalidArgumentException(details=str(e)) from e
            return make_flask_response(data=new_project.to_proto(), status=HTTPStatus.CREATED)

    @credentials_required
    def get(self):
        """Gets all projects.
        ---
        tags:
          - project
        description: gets all projects.
        responses:
          200:
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ProjectRef'
        """
        with db.session_scope() as session:
            service = ProjectService(session)
            return make_flask_response(data=service.get_projects())


class ProjectApi(Resource):

    @credentials_required
    @iam_required(Permission.PROJECT_GET)
    def get(self, project_id: int):
        """Gets a project.
        ---
        tags:
          - project
        description: Gets a project
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Project'
        """
        with db.session_scope() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if project is None:
                raise NotFoundException(f'Failed to find project: {project_id}')
            return make_flask_response(data=project.to_proto(), status=HTTPStatus.OK)

    @input_validator
    @credentials_required
    @iam_required(Permission.PROJECT_PATCH)
    @emits_event(audit_fields=['variables'])
    @use_kwargs({
        'comment': fields.String(load_default=None),
        'variables': fields.List(fields.Dict(), load_default=None),
        'config': fields.Dict(load_default=None)
    })
    def patch(self, project_id: int, comment: Optional[str], variables: Optional[List[Dict]], config: Optional[Dict]):
        """Patch a project.
        ---
        tags:
          - project
        description: Update a project.
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: body
          name: body
          schema:
            type: object
            properties:
              comment:
                type: string
              variables:
                description: A list of variables to override existing ones.
                type: array
                items:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Variable'
              config:
                description: Config of project, include variables.
                schema:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ProjectConfig'
        responses:
          200:
            description: Updated project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Project'
        """
        with db.session_scope() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if project is None:
                raise NotFoundException(f'Failed to find project: {project_id}')

            if comment:
                project.comment = comment

            if config is not None:
                config_proto = ParseDict(config, ProjectConfig(), ignore_unknown_fields=True)
                project.set_config(config_proto)
                session.flush()
            # TODO(xiangyuxuan.prs): remove variables parameter when pending project launch
            if variables is not None:
                # Overrides all variables
                variables = [ParseDict(variable, Variable()) for variable in variables]
                project.set_variables(variables)
            try:
                session.commit()
            except Exception as e:
                raise InvalidArgumentException(details=e) from e

            return make_flask_response(data=project.to_proto(), status=HTTPStatus.OK)


class CheckConnectionApi(Resource):

    @credentials_required
    def get(self, project_id: int):
        """Checks the connection for a project.
        ---
        tags:
          - project
        description: Checks the connection for a project.
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    success:
                      description: If the connection is established or not.
                      type: boolean
                    message:
                      type: string
        """
        with db.session_scope() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if project is None:
                raise NotFoundException(f'Failed to find project: {project_id}')
            service = ParticipantService(session)
            participants = service.get_platform_participants_by_project(project.id)

        error_messages = []
        for participant in participants:
            client = RpcClient.from_project_and_participant(project.name, project.token, participant.domain_name)
            result = client.check_connection().status
            if result.code != StatusCode.STATUS_SUCCESS:
                error_messages.append(
                    f'failed to validate {participant.domain_name}\'s workspace, result: {result.msg}')

        return {
            'data': {
                'success': len(error_messages) == 0,
                'message': '\n'.join(error_messages) if len(error_messages) > 0 else 'validate project successfully!'
            }
        }, HTTPStatus.OK


class ProjectParticipantsApi(Resource):

    @credentials_required
    def get(self, project_id: int):
        """Gets participants of a project.
        ---
        tags:
          - project
        description: Gets participants of a project.
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        responses:
          200:
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.Participant'
        """
        with db.session_scope() as session:
            project = session.query(Project).filter_by(id=project_id).first()
            if project is None:
                raise NotFoundException(f'Failed to find project: {project_id}')
            service = ParticipantService(session)
            participants = service.get_participants_by_project(project_id)
            return make_flask_response(data=[participant.to_proto() for participant in participants])


class PendingProjectsApi(Resource):

    @input_validator
    @credentials_required
    @iam_required(Permission.PROJECTS_POST)
    @use_args(CreatePendingProjectParameter())
    def post(self, data: Dict):
        """Creates a new pending project.
        ---
        tags:
          - project
        description: Creates a new pending project
        parameters:
        - in: body
          name: body
          schema:
            $ref: '#/definitions/CreatePendingProjectParameter'
        responses:
          201:
            description: Created a pending project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.PendingProjectPb'
        """
        with db.session_scope() as session:
            # TODO(xiangyuxuan.prs): remove after using token instead of name to ensure consistency of project
            if PendingProjectService(session).duplicated_name_exists(data['name']):
                raise ResourceConflictException(f'{data["name"]} has already existed')
            participants_info = PendingProjectService(session).build_participants_info(data['participant_ids'])
            pending_project = PendingProjectService(session).create_pending_project(data['name'],
                                                                                    data['config'],
                                                                                    participants_info,
                                                                                    data['comment'],
                                                                                    get_current_user().username,
                                                                                    state=PendingProjectState.ACCEPTED,
                                                                                    role=ProjectRole.COORDINATOR)
            session.flush()
            ticket_helper = get_ticket_helper(session)
            ticket_helper.create_ticket(TicketType.CREATE_PROJECT, TicketDetails(uuid=pending_project.uuid))
            session.commit()
            return make_flask_response(data=pending_project.to_proto(), status=HTTPStatus.CREATED)

    @credentials_required
    @use_args(
        {
            'filter': FilterExpField(
                required=False,
                load_default=None,
            ),
            'page': fields.Integer(required=False, load_default=1),
            'page_size': fields.Integer(required=False, load_default=10)
        },
        location='query')
    def get(self, params: dict):
        """Gets all pending projects.
        ---
        tags:
          - project
        description: gets all pending projects.
        responses:
          200:
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.PendingProjectPb'
        """
        with db.session_scope() as session:
            try:
                pagination = PendingProjectService(session).list_pending_projects(
                    filter_exp=params['filter'],
                    page=params['page'],
                    page_size=params['page_size'],
                )
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            data = [t.to_proto() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())


class PendingProjectApi(Resource):

    @credentials_required
    @use_kwargs({
        'state':
            fields.String(required=True,
                          validate=validate.OneOf([PendingProjectState.ACCEPTED.name, PendingProjectState.CLOSED.name]))
    })
    def patch(self, pending_project_id: int, state: str):
        """Accept or refuse a pending project.
        ---
        tags:
          - project
        description: Accept or refuse a pending project.
        parameters:
        - in: path
          name: pending_project_id
          schema:
            type: integer
        - in: body
          name: body
          schema:
            type: object
            properties:
              state:
                type: string
        responses:
          200:
            description: a pending project
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.PendingProjectPb'
        """
        with db.session_scope() as session:
            pending_project = PendingProjectService(session).update_state_as_participant(pending_project_id, state)
            resp = PendingProjectRpcController(pending_project).sync_pending_project_state_to_coordinator(
                uuid=pending_project.uuid, state=PendingProjectState(state))
            if not resp.succeeded:
                raise InternalException(f'connect to coordinator failed: {resp.msg}')
            session.commit()
            return make_flask_response(data=pending_project.to_proto())

    def delete(self, pending_project_id: int):
        """Delete pending project by id.
        ---
        tags:
          - project
        description: Delete pending project.
        parameters:
        - in: path
          name: pending_project_id
          required: true
          schema:
            type: integer
          description: The ID of the pending project
        responses:
          204:
            description: No content.
        """
        with db.session_scope() as session:
            pending_project = session.query(PendingProject).get(pending_project_id)
            if pending_project is None:
                return make_flask_response(status=HTTPStatus.NO_CONTENT)
        result = PendingProjectRpcController(pending_project).send_to_participants(
            partial(ProjectServiceClient.delete_pending_project, uuid=pending_project.uuid))
        if not all(resp.succeeded for resp in result.values()):
            raise InternalException(f'delete participants failed: {result}')
        with db.session_scope() as session:
            session.delete(pending_project)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


def initialize_project_apis(api: Api):
    api.add_resource(ProjectsApi, '/projects')
    api.add_resource(ProjectApi, '/projects/<int:project_id>')
    api.add_resource(ProjectParticipantsApi, '/projects/<int:project_id>/participants')
    api.add_resource(CheckConnectionApi, '/projects/<int:project_id>/connection_checks')

    api.add_resource(PendingProjectsApi, '/pending_projects')
    api.add_resource(PendingProjectApi, '/pending_project/<int:pending_project_id>')

    schema_manager.append(CreateProjectParameter)
    schema_manager.append(CreatePendingProjectParameter)
