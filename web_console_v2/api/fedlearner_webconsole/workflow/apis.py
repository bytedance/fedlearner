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

# pylint: disable=global-statement
# coding: utf-8
import json
import logging
from http import HTTPStatus
from typing import Optional, List

from flask_restful import Resource
from google.protobuf.json_format import MessageToDict
from sqlalchemy.orm import Session
from marshmallow import Schema, fields, validate, post_load

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (NotFoundException, InvalidArgumentException, InternalException)
from fedlearner_webconsole.iam.permission import Permission
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator, use_kwargs
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.flask_utils import download_json, get_current_user, make_flask_response, FilterExpField
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow.service import WorkflowService, \
    ForkWorkflowParams, CreateNewWorkflowParams
from fedlearner_webconsole.workflow_template.service import \
    dict_to_workflow_definition

from fedlearner_webconsole.iam.iam_required import iam_required
from fedlearner_webconsole.workflow.workflow_job_controller import start_workflow, stop_workflow, \
    invalidate_workflow_job
from fedlearner_webconsole.proto.audit_pb2 import Event


def _get_workflow(workflow_id: int, project_id: int, session: Session) -> Workflow:
    workflow_query = session.query(Workflow)
    # project_id 0 means search in all projects
    if project_id != 0:
        workflow_query = workflow_query.filter_by(project_id=project_id)
    workflow = workflow_query.filter_by(id=workflow_id).first()
    if workflow is None:
        raise NotFoundException()
    return workflow


class GetWorkflowsParameter(Schema):
    keyword = fields.String(required=False, load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)
    states = fields.List(fields.String(required=False,
                                       validate=validate.OneOf([
                                           'completed', 'failed', 'stopped', 'running', 'warmup', 'pending', 'ready',
                                           'configuring', 'invalid'
                                       ])),
                         required=False,
                         load_default=None)
    favour = fields.Integer(required=False, load_default=None, validate=validate.OneOf([0, 1]))
    uuid = fields.String(required=False, load_default=None)
    name = fields.String(required=False, load_default=None)
    template_revision_id = fields.Integer(required=False, load_default=None)
    filter_exp = FilterExpField(data_key='filter', required=False, load_default=None)


class PostWorkflowsParameter(Schema):
    name = fields.Str(required=True)
    config = fields.Dict(required=True)
    template_id = fields.Int(required=False, load_default=None)
    template_revision_id = fields.Int(required=False, load_default=None)
    forkable = fields.Bool(required=True)
    forked_from = fields.Int(required=False, load_default=None)
    create_job_flags = fields.List(required=False, load_default=None, cls_or_instance=fields.Int)
    peer_create_job_flags = fields.List(required=False, load_default=None, cls_or_instance=fields.Int)
    fork_proposal_config = fields.Dict(required=False, load_default=None)
    comment = fields.Str(required=False, load_default=None)
    cron_config = fields.Str(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['config'] = dict_to_workflow_definition(data['config'])
        data['fork_proposal_config'] = dict_to_workflow_definition(data['fork_proposal_config'])
        return data


class PutWorkflowParameter(Schema):
    config = fields.Dict(required=True)
    template_id = fields.Integer(required=False, load_default=None)
    template_revision_id = fields.Integer(required=False, load_default=None)
    forkable = fields.Boolean(required=True)
    create_job_flags = fields.List(required=False, load_default=None, cls_or_instance=fields.Integer)
    comment = fields.String(required=False, load_default=None)
    cron_config = fields.String(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['config'] = dict_to_workflow_definition(data['config'])
        return data


class PatchWorkflowParameter(Schema):
    config = fields.Dict(required=False, load_default=None)
    template_id = fields.Integer(required=False, load_default=None)
    template_revision_id = fields.Integer(required=False, load_default=None)
    forkable = fields.Boolean(required=False, load_default=None)
    create_job_flags = fields.List(required=False, load_default=None, cls_or_instance=fields.Integer)
    cron_config = fields.String(required=False, load_default=None)
    favour = fields.Boolean(required=False, load_default=None)
    metric_is_public = fields.Boolean(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['config'] = data['config'] and dict_to_workflow_definition(data['config'])
        return data


class PatchPeerWorkflowParameter(Schema):
    config = fields.Dict(required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        data['config'] = data['config'] and dict_to_workflow_definition(data['config'])
        return data


class WorkflowsApi(Resource):

    @credentials_required
    @use_kwargs(GetWorkflowsParameter(), location='query')
    def get(
        self,
        page: Optional[int],
        page_size: Optional[int],
        name: Optional[str],
        uuid: Optional[str],
        keyword: Optional[str],
        favour: Optional[bool],
        template_revision_id: Optional[int],
        states: Optional[List[str]],
        filter_exp: Optional[FilterExpression],
        project_id: int,
    ):
        """Get workflows.
        ---
        tags:
          - workflow
        description: Get workflows.
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
          description: The ID of the project. 0 means get all workflows.
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: name
          schema:
            type: string
        - in: query
          name: uuid
          schema:
            type: string
        - in: query
          name: keyword
          schema:
            type: string
        - in: query
          name: favour
          schema:
            type: boolean
        - in: query
          name: template_revision_id
          schema:
            type: integer
        - in: query
          name: states
          schema:
            type: array
            collectionFormat: multi
            items:
              type: string
              enum: [completed, failed, stopped, running, warmup, pending, ready, configuring, invalid]
        - in: query
          name: filter
          schema:
            type: string
        responses:
          200:
            description: list of workflows.
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowRef'
        """
        with db.session_scope() as session:
            result = session.query(Workflow)
            if project_id != 0:
                result = result.filter_by(project_id=project_id)
            if name is not None:
                result = result.filter_by(name=name)
            if keyword is not None:
                result = result.filter(Workflow.name.like(f'%{keyword}%'))
            if uuid is not None:
                result = result.filter_by(uuid=uuid)
            if favour is not None:
                result = result.filter_by(favour=favour)
            if states is not None:
                result = WorkflowService.filter_workflows(result, states)
            if template_revision_id is not None:
                result = result.filter_by(template_revision_id=template_revision_id)
            if filter_exp is not None:
                result = WorkflowService(session).build_filter_query(result, filter_exp)
            result = result.order_by(Workflow.id.desc())
            pagination = paginate(result, page, page_size)
            res = []
            for item in pagination.get_items():
                try:
                    wf_dict = to_dict(item.to_workflow_ref())
                except Exception as e:  # pylint: disable=broad-except
                    wf_dict = {
                        'id': item.id,
                        'name': item.name,
                        'uuid': item.uuid,
                        'error': f'Failed to get workflow state {repr(e)}'
                    }
                res.append(wf_dict)
            # To resolve the issue of that MySQL 8 Select Count(*) is very slow
            # https://bugs.mysql.com/bug.php?id=97709
            pagination.query = pagination.query.filter(Workflow.id > -1)
            page_meta = pagination.get_metadata()
            return make_flask_response(data=res, page_meta=page_meta)

    @input_validator
    @credentials_required
    @iam_required(Permission.WORKFLOWS_POST)
    @emits_event(resource_type=Event.ResourceType.WORKFLOW, audit_fields=['forkable'])
    @use_kwargs(PostWorkflowsParameter(), location='json')
    def post(
            self,
            name: str,
            comment: Optional[str],
            forkable: bool,
            forked_from: Optional[bool],
            create_job_flags: Optional[List[int]],
            peer_create_job_flags: Optional[List[int]],
            # Peer config
            fork_proposal_config: Optional[WorkflowDefinition],
            template_id: Optional[int],
            config: WorkflowDefinition,
            cron_config: Optional[str],
            template_revision_id: Optional[int],
            project_id: int):
        """Create workflows.
        ---
        tags:
          - workflow
        description: Get workflows.
        parameters:
        - in: path
          description: The ID of the project.
          name: project_id
          required: true
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PostWorkflowsParameter'
        responses:
          201:
            description: detail of workflows.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        with db.session_scope() as session:
            if forked_from:
                params = ForkWorkflowParams(fork_from_id=forked_from,
                                            fork_proposal_config=fork_proposal_config,
                                            peer_create_job_flags=peer_create_job_flags)
            else:
                params = CreateNewWorkflowParams(project_id=project_id,
                                                 template_id=template_id,
                                                 template_revision_id=template_revision_id)
            try:
                workflow = WorkflowService(session).create_workflow(name=name,
                                                                    comment=comment,
                                                                    forkable=forkable,
                                                                    config=config,
                                                                    create_job_flags=create_job_flags,
                                                                    cron_config=cron_config,
                                                                    params=params,
                                                                    creator_username=get_current_user().username)
            except ValueError as e:
                raise InvalidArgumentException(details=str(e)) from e
            session.commit()
            logging.info('Inserted a workflow to db')
            scheduler.wakeup(workflow.id)
            return make_flask_response(data=workflow.to_proto(), status=HTTPStatus.CREATED)


class WorkflowApi(Resource):

    @credentials_required
    @use_kwargs({'download': fields.Bool(required=False, load_default=False)}, location='query')
    def get(self, download: Optional[bool], project_id: int, workflow_id: int):
        """Get workflow and with jobs.
        ---
        tags:
          - workflow
        description: Get workflow.
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
          description: The ID of the project. 0 means get all workflows.
        - in: path
          name: workflow_id
          schema:
            type: integer
          required: true
        - in: query
          name: download
          schema:
            type: boolean
        responses:
          200:
            description: detail of workflow.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        del project_id
        with db.session_scope() as session:
            workflow = session.query(Workflow).get(workflow_id)
            if workflow is None:
                raise NotFoundException(f'workflow {workflow_id} is not found')
            result = workflow.to_proto()
            result.jobs.extend([job.to_proto() for job in workflow.get_jobs(session)])
            if download:
                return download_json(content=to_dict(result), filename=workflow.name)
            return make_flask_response(data=result)

    @credentials_required
    @iam_required(Permission.WORKFLOW_PUT)
    @emits_event(resource_type=Event.ResourceType.WORKFLOW, audit_fields=['forkable'])
    @use_kwargs(PutWorkflowParameter(), location='json')
    def put(self, config: WorkflowDefinition, template_id: Optional[int], forkable: bool,
            create_job_flags: Optional[List[int]], cron_config: Optional[str], comment: Optional[str],
            template_revision_id: Optional[int], project_id: int, workflow_id: int):
        """Config workflow.
        ---
        tags:
          - workflow
        description: Config workflow.
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
          description: The ID of the project.
        - in: path
          name: workflow_id
          required: true
          schema:
            type: integer
          description: The ID of the workflow.
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PutWorkflowParameter'
        responses:
          200:
            description: detail of workflow.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            try:
                WorkflowService(session).config_workflow(workflow=workflow,
                                                         template_id=template_id,
                                                         config=config,
                                                         forkable=forkable,
                                                         comment=comment,
                                                         cron_config=cron_config,
                                                         create_job_flags=create_job_flags,
                                                         creator_username=get_current_user().username,
                                                         template_revision_id=template_revision_id)
            except ValueError as e:
                raise InvalidArgumentException(details=str(e)) from e
            session.commit()
            scheduler.wakeup(workflow_id)
            logging.info('update workflow %d target_state to %s', workflow.id, workflow.target_state)
            return make_flask_response(data=workflow.to_proto())

    @input_validator
    @credentials_required
    @iam_required(Permission.WORKFLOW_PATCH)
    @emits_event(resource_type=Event.ResourceType.WORKFLOW, audit_fields=['forkable', 'metric_is_public'])
    @use_kwargs(PatchWorkflowParameter(), location='json')
    def patch(self, forkable: Optional[bool], metric_is_public: Optional[bool], config: Optional[WorkflowDefinition],
              template_id: Optional[int], create_job_flags: Optional[List[int]], cron_config: Optional[str],
              favour: Optional[bool], template_revision_id: Optional[int], project_id: int, workflow_id: int):
        """Patch workflow.
        ---
        tags:
          - workflow
        description: Patch workflow.
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
          description: The ID of the project.
        - in: path
          name: workflow_id
          required: true
          schema:
            type: integer
          description: The ID of the workflow.
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PatchWorkflowParameter'
        responses:
          200:
            description: detail of workflow.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            try:
                WorkflowService(session).patch_workflow(workflow=workflow,
                                                        forkable=forkable,
                                                        metric_is_public=metric_is_public,
                                                        config=config,
                                                        template_id=template_id,
                                                        create_job_flags=create_job_flags,
                                                        cron_config=cron_config,
                                                        favour=favour,
                                                        template_revision_id=template_revision_id)
                session.commit()
            except ValueError as e:
                raise InvalidArgumentException(details=str(e)) from e
            return make_flask_response(data=workflow.to_proto())


class PeerWorkflowsApi(Resource):

    @credentials_required
    def get(self, project_id: int, workflow_id: int):
        """Get peer workflow and with jobs.
        ---
        tags:
          - workflow
        description: Get peer workflow.
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
        - in: path
          name: workflow_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of workflow.
            content:
              application/json:
                schema:
                  type: object
                  additionalProperties:
                    $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        peer_workflows = {}
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            service = ParticipantService(session)
            participants = service.get_platform_participants_by_project(workflow.project.id)

            for participant in participants:
                client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                                participant.domain_name)
                # TODO(xiangyxuan): use uuid to identify the workflow
                resp = client.get_workflow(workflow.uuid, workflow.name)
                if resp.status.code != common_pb2.STATUS_SUCCESS:
                    raise InternalException(resp.status.msg)
                peer_workflow = MessageToDict(resp,
                                              preserving_proto_field_name=True,
                                              including_default_value_fields=True)
                for job in peer_workflow['jobs']:
                    if 'pods' in job:
                        job['pods'] = json.loads(job['pods'])
                peer_workflows[participant.name] = peer_workflow
            return make_flask_response(peer_workflows)

    @credentials_required
    @iam_required(Permission.WORKFLOW_PATCH)
    @use_kwargs(PatchPeerWorkflowParameter(), location='json')
    def patch(self, config: WorkflowDefinition, project_id: int, workflow_id: int):
        """Patch peer workflow.
        ---
        tags:
          - workflow
        description: patch peer workflow.
        parameters:
        - in: path
          name: project_id
          required: true
          schema:
            type: integer
        - in: path
          name: workflow_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/PatchPeerWorkflowParameter'
        responses:
          200:
            description: detail of workflow.
            content:
              application/json:
                schema:
                  type: object
                  additionalProperties:
                    $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        peer_workflows = {}
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            service = ParticipantService(session)
            participants = service.get_platform_participants_by_project(workflow.project.id)
            for participant in participants:
                client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                                participant.domain_name)
                resp = client.update_workflow(workflow.uuid, workflow.name, config)
                if resp.status.code != common_pb2.STATUS_SUCCESS:
                    raise InternalException(resp.status.msg)
                peer_workflows[participant.name] = MessageToDict(resp,
                                                                 preserving_proto_field_name=True,
                                                                 including_default_value_fields=True)
            return make_flask_response(peer_workflows)


class WorkflowInvalidateApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.WORKFLOW, op_type=Event.OperationType.INVALIDATE)
    def post(self, project_id: int, workflow_id: int):
        """Invalidates the workflow job.
        ---
        tags:
          - workflow
        description: Invalidates the workflow job.
        parameters:
          - in: path
            name: project_id
            schema:
              type: integer
          - in: path
            name: workflow_id
            schema:
              type: integer
        responses:
          200:
            description: Invalidated workflow
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            invalidate_workflow_job(session, workflow)
            session.commit()
            return make_flask_response(workflow.to_proto())


class WorkflowStartApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.WORKFLOW, op_type=Event.OperationType.UPDATE)
    def post(self, project_id: int, workflow_id: int):
        """Starts the workflow job.
        ---
        tags:
          - workflow
        description: Starts the workflow job.
        parameters:
          - in: path
            name: project_id
            schema:
              type: integer
          - in: path
            name: workflow_id
            schema:
              type: integer
        responses:
          200:
            description: Started workflow
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        start_workflow(workflow_id)
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            return make_flask_response(workflow.to_proto())


class WorkflowStopApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.WORKFLOW, op_type=Event.OperationType.UPDATE)
    def post(self, project_id: int, workflow_id: int):
        """Stops the workflow job.
        ---
        tags:
          - workflow
        description: Stops the workflow job.
        parameters:
          - in: path
            name: project_id
            schema:
              type: integer
          - in: path
            name: workflow_id
            schema:
              type: integer
        responses:
          200:
            description: Stopped workflow
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.WorkflowPb'
        """
        stop_workflow(workflow_id)
        with db.session_scope() as session:
            workflow = _get_workflow(workflow_id, project_id, session)
            return make_flask_response(workflow.to_proto())


def initialize_workflow_apis(api):
    api.add_resource(WorkflowsApi, '/projects/<int:project_id>/workflows')
    api.add_resource(WorkflowApi, '/projects/<int:project_id>/workflows/<int:workflow_id>')
    api.add_resource(PeerWorkflowsApi, '/projects/<int:project_id>/workflows/<int:workflow_id>/peer_workflows')
    api.add_resource(WorkflowInvalidateApi, '/projects/<int:project_id>/workflows/<int:workflow_id>:invalidate')
    api.add_resource(WorkflowStartApi, '/projects/<int:project_id>/workflows/<int:workflow_id>:start')
    api.add_resource(WorkflowStopApi, '/projects/<int:project_id>/workflows/<int:workflow_id>:stop')

    # if a schema is used, one has to append it to schema_manager so Swagger knows there is a schema available
    schema_manager.append(PostWorkflowsParameter)
    schema_manager.append(PutWorkflowParameter)
    schema_manager.append(PatchWorkflowParameter)
    schema_manager.append(PatchPeerWorkflowParameter)
