# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import logging
import json
from uuid import uuid4
from http import HTTPStatus
from flask_restful import Resource, reqparse, request
from google.protobuf.json_format import MessageToDict
from fedlearner_webconsole.workflow.models import (
    Workflow, WorkflowState, TransactionState
)
from fedlearner_webconsole.job.yaml_formatter import generate_job_run_yaml
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.workflow_template.apis import \
    dict_to_workflow_definition
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (
    NotFoundException, ResourceConflictException, InvalidArgumentException,
    InternalException, NoAccessException)
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.rpc.client import RpcClient


def _get_workflow(workflow_id):
    result = Workflow.query.filter_by(id=workflow_id).first()
    if result is None:
        raise NotFoundException()
    return result


class WorkflowsApi(Resource):
    def get(self):
        result = Workflow.query
        if 'project' in request.args and request.args['project'] is not None:
            project_id = request.args['project']
            result = result.filter_by(project_id=project_id)
        if 'keyword' in request.args and request.args['keyword'] is not None:
            keyword = request.args['keyword']
            result = result.filter(Workflow.name.like(
                '%{}%'.format(keyword)))
        if 'uuid' in request.args and request.args['uuid'] is not None:
            uuid = request.args['uuid']
            result = result.filter_by(uuid=uuid)
        return {'data': [row.to_dict() for row in
                         result.order_by(
                             Workflow.created_at.desc()).all()]}, HTTPStatus.OK

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, help='name is empty')
        parser.add_argument('project_id', type=int, required=True,
                            help='project_id is empty')
        # TODO: should verify if the config is compatible with
        # workflow template
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('forkable', type=bool, required=True,
                            help='forkable is empty')
        parser.add_argument('forked_from', type=int, required=False,
                            help='fork from base workflow')
        parser.add_argument('reuse_job_names', type=list, required=False,
                            location='json', help='fork and inherit jobs')
        parser.add_argument('peer_reuse_job_names', type=list,
                            required=False, location='json',
                            help='peer fork and inherit jobs')
        parser.add_argument('fork_proposal_config', type=dict, required=False,
                            help='fork and edit peer config')
        parser.add_argument('comment')
        data = parser.parse_args()
        name = data['name']
        if Workflow.query.filter_by(name=name).first() is not None:
            raise ResourceConflictException(
                'Workflow {} already exists.'.format(name))

        # form to proto buffer
        template_proto = dict_to_workflow_definition(data['config'])
        workflow = Workflow(name=name,
                            # 20 bytes
                            # a DNS-1035 label must start with an
                            # alphabetic character. substring uuid[:19] has
                            # no collision in 10 million draws
                            uuid=f'u{uuid4().hex[:19]}',
                            comment=data['comment'],
                            project_id=data['project_id'],
                            forkable=data['forkable'],
                            forked_from=data['forked_from'],
                            state=WorkflowState.NEW,
                            target_state=WorkflowState.READY,
                            transaction_state=TransactionState.READY)

        if workflow.forked_from is not None:
            fork_config = dict_to_workflow_definition(
                data['fork_proposal_config'])
            # TODO: more validations
            if len(fork_config.job_definitions) != \
                    len(template_proto.job_definitions):
                raise InvalidArgumentException(
                    'Forked workflow\'s template does not match base workflow')
            workflow.set_fork_proposal_config(fork_config)
            workflow.set_reuse_job_names(data['reuse_job_names'])
            workflow.set_peer_reuse_job_names(data['peer_reuse_job_names'])

        workflow.set_config(template_proto)
        db.session.add(workflow)
        db.session.commit()
        logging.info('Inserted a workflow to db')
        scheduler.wakeup(workflow.id)
        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


class WorkflowApi(Resource):
    def get(self, workflow_id):
        workflow = _get_workflow(workflow_id)
        result = workflow.to_dict()
        result['jobs'] = [job.to_dict() for job in workflow.get_jobs()]
        result['owned_jobs'] = [job.to_dict() for job in workflow.owned_jobs]
        result['config'] = None
        if workflow.get_config() is not None:
            result['config'] = MessageToDict(
                            workflow.get_config(),
                            preserving_proto_field_name=True,
                            including_default_value_fields=True)
        return {'data': result}, HTTPStatus.OK

    def put(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('forkable', type=bool, required=True,
                            help='forkable is empty')
        parser.add_argument('comment')
        data = parser.parse_args()

        workflow = _get_workflow(workflow_id)
        if workflow.config:
            raise ResourceConflictException(
                'Resetting workflow is not allowed')

        workflow.comment = data['comment']
        workflow.forkable = data['forkable']
        workflow.set_config(dict_to_workflow_definition(data['config']))
        workflow.update_target_state(WorkflowState.READY)
        db.session.commit()
        scheduler.wakeup(workflow_id)
        logging.info('update workflow %d target_state to %s',
                     workflow.id, workflow.target_state)
        return {'data': workflow.to_dict()}, HTTPStatus.OK

    def patch(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('target_state', type=str, required=False,
                            default=None, help='target_state is empty')
        parser.add_argument('state', type=str, required=False,
                            default=None, help='state is empty')
        parser.add_argument('forkable', type=bool)
        parser.add_argument('metric_is_public', type=bool)
        parser.add_argument('config', type=dict, required=False,
                            default=None, help='updated config')
        data = parser.parse_args()

        workflow = _get_workflow(workflow_id)

        forkable = data['forkable']
        if forkable is not None:
            workflow.forkable = forkable
            db.session.flush()

        metric_is_public = data['metric_is_public']
        if metric_is_public is not None:
            workflow.metric_is_public = metric_is_public
            db.session.flush()

        target_state = data['target_state']
        if target_state:
            try:
                if WorkflowState[target_state] == WorkflowState.RUNNING:
                    for job in workflow.owned_jobs:
                        try:
                            generate_job_run_yaml(job)
                        # TODO: check if peer variables is valid
                        except RuntimeError as e:
                            raise ValueError(
                                f'Invalid Variable when try '
                                f'to format the job {job.name}:{str(e)}')
                workflow.update_target_state(WorkflowState[target_state])
                db.session.flush()
                logging.info('updated workflow %d target_state to %s',
                            workflow.id, workflow.target_state)
                scheduler.wakeup(workflow.id)
            except ValueError as e:
                raise InvalidArgumentException(details=str(e)) from e

        state = data['state']
        if state:
            try:
                assert state == 'INVALID', \
                    'Can only set state to INVALID for invalidation'
                workflow.invalidate()
                db.session.flush()
                logging.info('invalidate workflow %d', workflow.id)
            except ValueError as e:
                raise InvalidArgumentException(details=str(e)) from e

        config = data['config']
        if config:
            try:
                if workflow.target_state != WorkflowState.INVALID or \
                        workflow.state not in \
                        [WorkflowState.READY, WorkflowState.STOPPED]:
                    raise NoAccessException('Cannot edit running workflow')
                config_proto = dict_to_workflow_definition(data['config'])
                workflow.set_config(config_proto)
                db.session.flush()
            except ValueError as e:
                raise InvalidArgumentException(details=str(e)) from e

        db.session.commit()
        return {'data': workflow.to_dict()}, HTTPStatus.OK


class PeerWorkflowsApi(Resource):
    def get(self, workflow_id):
        workflow = _get_workflow(workflow_id)
        project_config = workflow.project.get_config()
        peer_workflows = {}
        for party in project_config.participants:
            client = RpcClient(project_config, party)
            # TODO(xiangyxuan): use uuid to identify the workflow
            resp = client.get_workflow(workflow.name)
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                raise InternalException(resp.status.msg)
            peer_workflow = MessageToDict(
                resp,
                preserving_proto_field_name=True,
                including_default_value_fields=True)
            for job in peer_workflow['jobs']:
                if 'pods' in job:
                    job['pods'] = json.loads(job['pods'])
            peer_workflows[party.name] = peer_workflow
        return {'data': peer_workflows}, HTTPStatus.OK

    def patch(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('config', type=dict, required=True,
                            help='new config for peer')
        data = parser.parse_args()
        config_proto = dict_to_workflow_definition(data['config'])

        workflow = _get_workflow(workflow_id)
        project_config = workflow.project.get_config()
        peer_workflows = {}
        for party in project_config.participants:
            client = RpcClient(project_config, party)
            resp = client.update_workflow(
                workflow.name, config_proto)
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                raise InternalException(resp.status.msg)
            peer_workflows[party.name] = MessageToDict(
                resp,
                preserving_proto_field_name=True,
                including_default_value_fields=True)
        return {'data': peer_workflows}, HTTPStatus.OK


def initialize_workflow_apis(api):
    api.add_resource(WorkflowsApi, '/workflows')
    api.add_resource(WorkflowApi, '/workflows/<int:workflow_id>')
    api.add_resource(PeerWorkflowsApi,
                     '/workflows/<int:workflow_id>/peer_workflows')
