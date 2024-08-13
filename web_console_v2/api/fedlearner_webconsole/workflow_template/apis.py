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

import grpc
from flask_restful import Resource
from sqlalchemy.orm import undefer
from marshmallow import fields, Schema, post_load
from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.proto.workflow_template_pb2 import WorkflowTemplateRevisionJson
from fedlearner_webconsole.rpc.v2.project_service_client import ProjectServiceClient
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator, use_args, use_kwargs
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.flask_utils import download_json, make_flask_response, get_current_user, FilterExpField
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateRevision, \
    WorkflowTemplateKind
from fedlearner_webconsole.workflow_template.service import (WorkflowTemplateService, _format_template_with_yaml_editor,
                                                             _check_config_and_editor_info,
                                                             WorkflowTemplateRevisionService)
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import NotFoundException, InvalidArgumentException, ResourceConflictException, \
    NetworkException
from fedlearner_webconsole.proto.workflow_template_pb2 import WorkflowTemplateJson


class PostWorkflowTemplatesParams(Schema):
    config = fields.Dict(required=True)
    editor_info = fields.Dict(required=False, load_default={})
    name = fields.String(required=True)
    comment = fields.String(required=False, load_default=None)
    kind = fields.Integer(required=False, load_default=0)

    @post_load()
    def make(self, data, **kwargs):
        data['config'], data['editor_info'] = _check_config_and_editor_info(data['config'], data['editor_info'])
        return data


class PutWorkflowTemplatesParams(Schema):
    config = fields.Dict(required=True)
    editor_info = fields.Dict(required=False, load_default={})
    name = fields.String(required=True)
    comment = fields.String(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['config'], data['editor_info'] = _check_config_and_editor_info(data['config'], data['editor_info'])
        return data


class GetWorkflowTemplatesParams(Schema):
    filter = FilterExpField(required=False, load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)


class WorkflowTemplatesApi(Resource):

    @credentials_required
    @use_args(GetWorkflowTemplatesParams(), location='query')
    def get(self, params: dict):
        """Get templates.
        ---
        tags:
          - workflow_template
        description: Get templates list.
        parameters:
        - in: query
          name: filter
          schema:
            type: string
          required: true
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
            description: list of workflow templates.
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplateRef'
        """
        with db.session_scope() as session:
            try:
                pagination = WorkflowTemplateService(session).list_workflow_templates(
                    filter_exp=params['filter'],
                    page=params['page'],
                    page_size=params['page_size'],
                )
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            data = [t.to_ref() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @input_validator
    @credentials_required
    @emits_event(audit_fields=['name'])
    @use_args(PostWorkflowTemplatesParams(), location='json')
    def post(self, params: dict):
        """Create a workflow_template.
        ---
        tags:
          - workflow_template
        description: Create a template.
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PostWorkflowTemplatesParams'
          required: true
        responses:
          201:
            description: detail of workflow template.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplatePb'
        """
        with db.session_scope() as session:
            template = WorkflowTemplateService(session).post_workflow_template(
                name=params['name'],
                comment=params['comment'],
                config=params['config'],
                editor_info=params['editor_info'],
                kind=params['kind'],
                creator_username=get_current_user().username)
            session.commit()
            return make_flask_response(data=template.to_proto(), status=HTTPStatus.CREATED)


class WorkflowTemplateApi(Resource):

    @credentials_required
    @use_args({'download': fields.Bool(required=False, load_default=False)}, location='query')
    def get(self, params: dict, template_id: int):
        """Get template by id.
        ---
        tags:
          - workflow_template
        description: Get a template.
        parameters:
        - in: path
          name: template_id
          schema:
            type: integer
          required: true
        - in: query
          name: download
          schema:
            type: boolean
        responses:
          200:
            description: detail of workflow template.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplatePb'
        """
        with db.session_scope() as session:
            template = session.query(WorkflowTemplate).filter_by(id=template_id).first()
            if template is None:
                raise NotFoundException(f'Failed to find template: {template_id}')
            template_proto = template.to_proto()
            if params['download']:
                # Note this is a workaround to removes some fields from the proto.
                # WorkflowTemplateJson and WorkflowTemplatePb are compatible.
                template_json_pb = WorkflowTemplateJson()
                template_json_pb.ParseFromString(template_proto.SerializeToString())
                return download_json(content=to_dict(template_json_pb), filename=template.name)
            return make_flask_response(template_proto)

    @credentials_required
    @emits_event()
    def delete(self, template_id):
        """delete template by id.
        ---
        tags:
          - workflow_template
        description: Delete a template.
        parameters:
        - in: path
          name: template_id
          schema:
            type: integer
          required: true
        responses:
          204:
            description: Successfully deleted.
        """
        with db.session_scope() as session:
            result = session.query(WorkflowTemplate).filter_by(id=template_id)
            if result.first() is None:
                raise NotFoundException(f'Failed to find template: {template_id}')
            result.delete()
            session.commit()
            return make_flask_response(status=HTTPStatus.NO_CONTENT)

    @input_validator
    @credentials_required
    @emits_event(audit_fields=['name'])
    @use_args(PutWorkflowTemplatesParams(), location='json')
    def put(self, params: dict, template_id: int):
        """Put a workflow_template.
        ---
        tags:
          - workflow_template
        description: edit a template.
        parameters:
        - in: path
          name: template_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PutWorkflowParams'
          required: true
        responses:
          200:
            description: detail of workflow template.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplatePb'
        """
        with db.session_scope() as session:
            tmp = session.query(WorkflowTemplate).filter_by(name=params['name']).first()
            if tmp is not None and tmp.id != template_id:
                raise ResourceConflictException(f'Workflow template {params["name"]} already exists')
            template = session.query(WorkflowTemplate).filter_by(id=template_id).first()
            if template is None:
                raise NotFoundException(f'Failed to find template: {template_id}')
            template_proto = _format_template_with_yaml_editor(params['config'], params['editor_info'], session)
            template.set_config(template_proto)
            template.set_editor_info(params['editor_info'])
            template.name = params['name']
            template.comment = params['comment']
            template.group_alias = template_proto.group_alias
            session.commit()
            return make_flask_response(template.to_proto())


class WorkflowTemplateRevisionsApi(Resource):

    @credentials_required
    @use_args(
        {
            'page': fields.Integer(required=False, load_default=None),
            'page_size': fields.Integer(required=False, load_default=None)
        },
        location='query')
    def get(self, params: dict, template_id: int):
        """Get all template revisions for specific template.
        ---
        tags:
          - workflow_template
        description: Get all template revisions for specific template.
        parameters:
        - in: path
          name: template_id
          required: true
          schema:
            type: integer
          description: The ID of the template
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
            description: list of workflow template revisions.
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplateRevisionRef'
        """
        with db.session_scope() as session:
            query = session.query(WorkflowTemplateRevision).filter_by(template_id=template_id)
            query = query.order_by(WorkflowTemplateRevision.revision_index.desc())
            pagination = paginate(query, params['page'], params['page_size'])
            data = [t.to_ref() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())


class WorkflowTemplateRevisionsCreateApi(Resource):

    @credentials_required
    def post(self, template_id: int):
        """Create a new template revision for specific template if config has been changed.
        ---
        tags:
          - workflow_template
        description: Create a new template revision for specific template if config has been changed.
        parameters:
        - in: path
          name: template_id
          required: true
          schema:
            type: integer
          description: The ID of the template
        responses:
          200:
            description: detail of workflow template revision.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplateRevisionPb'
        """
        with db.session_scope() as session:
            revision = WorkflowTemplateRevisionService(session).create_new_revision_if_template_updated(
                template_id=template_id)
            session.commit()
            return make_flask_response(data=revision.to_proto())


class WorkflowTemplateRevisionApi(Resource):

    @credentials_required
    @use_args({'download': fields.Boolean(required=False, load_default=None)}, location='query')
    def get(self, params: dict, revision_id: int):
        """Get template revision by id.
        ---
        tags:
          - workflow_template
        description: Get template revision.
        parameters:
        - in: path
          name: revision_id
          required: true
          schema:
            type: integer
          description: The ID of the template revision
        - in: query
          name: download
          schema:
            type: boolean
        responses:
          200:
            description: detail of workflow template revision.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplateRevisionPb'
        """
        with db.session_scope() as session:
            template_revision = session.query(WorkflowTemplateRevision).options(
                undefer(WorkflowTemplateRevision.config),
                undefer(WorkflowTemplateRevision.editor_info)).get(revision_id)
            if template_revision is None:
                raise NotFoundException(f'Cant not find template revision {revision_id}')
            if params['download']:
                # Note this is a workaround to removes some fields from the proto.
                # WorkflowTemplateRevisionJson and WorkflowTemplateRevisionPb are compatible.
                revision_proto = template_revision.to_proto()
                revision_json_pb = WorkflowTemplateRevisionJson()
                revision_json_pb.ParseFromString(revision_proto.SerializeToString())
                return download_json(content=to_dict(revision_json_pb), filename=template_revision.id)
            return make_flask_response(data=template_revision.to_proto())

    @credentials_required
    def delete(self, revision_id: int):
        """Delete template revision by id.
        ---
        tags:
          - workflow_template
        description: Delete template revision.
        parameters:
        - in: path
          name: revision_id
          required: true
          schema:
            type: integer
          description: The ID of the template revision
        responses:
          204:
            description: No content.
        """
        with db.session_scope() as session:
            WorkflowTemplateRevisionService(session).delete_revision(revision_id=revision_id)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)

    @credentials_required
    @use_args({'comment': fields.String(required=False, load_default=None)})
    def patch(self, params: dict, revision_id: int):
        """Patch template revision by id.
        ---
        tags:
          - workflow_template
        description: Patch template revision.
        parameters:
        - in: path
          name: revision_id
          required: true
          schema:
            type: integer
          description: The ID of the template revision
        - in: body
          name: comment
          schema:
            type: string
          required: false
        responses:
          200:
            description: detail of workflow template revision.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowTemplateRevisionPb'
        """
        with db.session_scope() as session:
            template_revision = session.query(WorkflowTemplateRevision).options(
                undefer(WorkflowTemplateRevision.config),
                undefer(WorkflowTemplateRevision.editor_info)).get(revision_id)
            if template_revision is None:
                raise NotFoundException(f'Cant not find template revision {revision_id}')
            if params['comment']:
                template_revision.comment = params['comment']
            session.commit()
            return make_flask_response(data=template_revision.to_proto())


class WorkflowTemplateRevisionSendApi(Resource):

    @use_kwargs({
        'participant_id': fields.Integer(required=True),
    }, location='query')
    def post(self, revision_id: int, participant_id: int):
        """Send a template revision to participant.
        ---
        tags:
          - workflow_template
        description: Send a template revision to participant.
        parameters:
        - in: path
          name: revision_id
          required: true
          schema:
            type: integer
          description: The ID of the template revision
        - in: query
          name: participant_id
          required: true
          schema:
            type: integer
          description: The ID of the participant
        responses:
          204:
            description: No content.
        """
        with db.session_scope() as session:
            part: Participant = session.query(Participant).get(participant_id)
            if part is None:
                raise NotFoundException(f'participant {participant_id} is not exist')
            revision: WorkflowTemplateRevision = session.query(WorkflowTemplateRevision).get(revision_id)
            if revision is None:
                raise NotFoundException(f'participant {revision_id} is not exist')
            try:
                ProjectServiceClient.from_participant(part.domain_name).send_template_revision(
                    config=revision.get_config(),
                    name=revision.template.name,
                    comment=revision.comment,
                    kind=WorkflowTemplateKind.PEER,
                    revision_index=revision.revision_index)
            except grpc.RpcError as e:
                raise NetworkException(str(e)) from e

        return make_flask_response(status=HTTPStatus.NO_CONTENT)


def initialize_workflow_template_apis(api):
    api.add_resource(WorkflowTemplatesApi, '/workflow_templates')
    api.add_resource(WorkflowTemplateApi, '/workflow_templates/<int:template_id>')
    api.add_resource(WorkflowTemplateRevisionsApi, '/workflow_templates/<int:template_id>/workflow_template_revisions')
    api.add_resource(WorkflowTemplateRevisionsCreateApi, '/workflow_templates/<int:template_id>:create_revision')
    api.add_resource(WorkflowTemplateRevisionApi, '/workflow_template_revisions/<int:revision_id>')
    api.add_resource(WorkflowTemplateRevisionSendApi, '/workflow_template_revisions/<int:revision_id>:send')

    # if a schema is used, one has to append it to schema_manager so Swagger knows there is a schema available
    schema_manager.append(PostWorkflowTemplatesParams)
    schema_manager.append(PutWorkflowTemplatesParams)
