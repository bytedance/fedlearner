# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from fedlearner_webconsole.composer.models import ItemStatus
from fedlearner_webconsole.utils.decorators import jwt_required
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
from fedlearner_webconsole.composer.composer import composer
from fedlearner_webconsole.workflow.cronjob import WorkflowCronJobItem
from fedlearner_webconsole.utils.metrics import emit_counter


def _get_workflow(workflow_id) -> Workflow:
    result = Workflow.query.filter_by(id=workflow_id).first()
    if result is None:
        raise NotFoundException()
    return result

def start_or_stop_cronjob(batch_update_interval: int, workflow: Workflow):
    """start a cronjob for workflow if batch_update_interval is valid

    Args:
        batch_update_interval (int): restart workflow interval, unit is minutes

    Returns:
        raise when workflow is_left is False
    """
    item_name = f'workflow_cron_job_{workflow.id}'
    batch_update_interval = batch_update_interval * 60
    if workflow.get_config().is_left and batch_update_interval > 0:
        status = composer.get_item_status(name=item_name)
        # create a cronjob
        if not status:
            composer.collect(name=item_name,
                                items=[WorkflowCronJobItem(workflow.id)],
                                metadata={},
                                interval=batch_update_interval)
            return
        if status == ItemStatus.OFF:
            raise InvalidArgumentException(
                f'cannot set item [{item_name}], since item is off')
        # patch a cronjob
        try:
            composer.patch_item_attr(name=item_name,
                                     key='interval_time',
                                     value=batch_update_interval)
        except ValueError as err:
            raise InvalidArgumentException(details=repr(err))


    elif batch_update_interval < 0:
        composer.finish(name=item_name)
    elif not workflow.get_config().is_left:
        raise InvalidArgumentException('Only left can operate this')
    else:
        logging.info('skip cronjob since batch_update_interval is -1')

def is_peer_job_inheritance_matched(workflow):
    # TODO: Move it to workflow service
    if workflow.forked_from is None:
        return True
    job_flags = workflow.get_create_job_flags()
    peer_job_flags = workflow.get_peer_create_job_flags()
    job_defs = workflow.get_config().job_definitions
    project = workflow.project
    if project is None:
        return True
    project_config = project.get_config()
    # TODO: Fix for multi-peer
    client = RpcClient(project_config, project_config.participants[0])
    parent_workflow = db.session.query(Workflow).get(workflow.forked_from)
    resp = client.get_workflow(parent_workflow.name)
    if resp.status.code != common_pb2.STATUS_SUCCESS:
        emit_counter('get_workflow_failed', 1)
        raise InternalException(resp.status.msg)
    peer_job_defs = resp.config.job_definitions
    for i, job_def in enumerate(job_defs):
        if job_def.is_federated:
            for j, peer_job_def in enumerate(peer_job_defs):
                if job_def.name == peer_job_def.name:
                    if job_flags[i] != peer_job_flags[j]:
                        return False
    return True

class WorkflowsApi(Resource):
    @jwt_required()
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
        res = []
        for row in result.order_by(Workflow.created_at.desc()).all():
            try:
                wf_dict = row.to_dict()
            except Exception as e:  # pylint: disable=broad-except
                wf_dict = {
                    'id': row.id,
                    'name': row.name,
                    'uuid': row.uuid,
                    'error': f'Failed to get workflow state {repr(e)}'
                }
            res.append(wf_dict)
        return {'data': res}, HTTPStatus.OK

    @jwt_required()
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
        parser.add_argument('create_job_flags', type=list, required=False,
                            location='json',
                            help='flags in common.CreateJobFlag')
        parser.add_argument('peer_create_job_flags', type=list,
                            required=False, location='json',
                            help='peer flags in common.CreateJobFlag')
        parser.add_argument('fork_proposal_config', type=dict, required=False,
                            help='fork and edit peer config')
        parser.add_argument('batch_update_interval',
                            type=int,
                            required=False,
                            help='interval for workflow cronjob in minute')
        parser.add_argument('extra',
                            type=str,
                            required=False,
                            help='extra json string that needs send to peer')

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
                            transaction_state=TransactionState.READY,
                            extra=data['extra']
                            )
        workflow.set_config(template_proto)
        workflow.set_create_job_flags(data['create_job_flags'])

        if workflow.forked_from is not None:
            fork_config = dict_to_workflow_definition(
                data['fork_proposal_config'])
            # TODO: more validations
            if len(fork_config.job_definitions) != \
                    len(template_proto.job_definitions):
                raise InvalidArgumentException(
                    'Forked workflow\'s template does not match base workflow')
            workflow.set_fork_proposal_config(fork_config)
            workflow.set_peer_create_job_flags(data['peer_create_job_flags'])
            if not is_peer_job_inheritance_matched(workflow):
                raise InvalidArgumentException('Forked workflow has federated \
                                               job with unmatched inheritance')

        db.session.add(workflow)
        db.session.commit()
        logging.info('Inserted a workflow to db')
        scheduler.wakeup(workflow.id)

        # start cronjob every interval time
        # should start after inserting to db
        batch_update_interval = data['batch_update_interval']
        if batch_update_interval:
            start_or_stop_cronjob(batch_update_interval, workflow)

        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


class WorkflowApi(Resource):
    @jwt_required()
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

    @jwt_required()
    def put(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('forkable', type=bool, required=True,
                            help='forkable is empty')
        parser.add_argument('create_job_flags', type=list, required=False,
                            location='json',
                            help='flags in common.CreateJobFlag')
        parser.add_argument(
            'batch_update_interval',
            type=int,
            required=False,
            help='interval time for cronjob of workflow in minute')
        parser.add_argument('comment')
        data = parser.parse_args()

        workflow = _get_workflow(workflow_id)
        if workflow.config:
            raise ResourceConflictException(
                'Resetting workflow is not allowed')

        batch_update_interval = data['batch_update_interval']
        if batch_update_interval:
            start_or_stop_cronjob(batch_update_interval, workflow)

        workflow.comment = data['comment']
        workflow.forkable = data['forkable']
        workflow.set_config(dict_to_workflow_definition(data['config']))
        workflow.set_create_job_flags(data['create_job_flags'])
        workflow.update_target_state(WorkflowState.READY)
        db.session.commit()
        scheduler.wakeup(workflow_id)
        logging.info('update workflow %d target_state to %s',
                     workflow.id, workflow.target_state)
        return {'data': workflow.to_dict()}, HTTPStatus.OK

    @jwt_required()
    def patch(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('target_state', type=str, required=False,
                            default=None, help='target_state is empty')
        parser.add_argument('state',
                            type=str,
                            required=False,
                            help='state is empty')
        parser.add_argument('forkable', type=bool)
        parser.add_argument('metric_is_public', type=bool)
        parser.add_argument('config',
                            type=dict,
                            required=False,
                            help='updated config')
        parser.add_argument('create_job_flags', type=list, required=False,
                            location='json',
                            help='flags in common.CreateJobFlag')
        parser.add_argument('batch_update_interval',
                            type=int,
                            required=False,
                            help='interval for restart workflow in minute')
        data = parser.parse_args()

        workflow = _get_workflow(workflow_id)

        # start workflow every interval time
        batch_update_interval = data['batch_update_interval']
        if batch_update_interval:
            start_or_stop_cronjob(batch_update_interval, workflow)

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
                        except Exception as e:  # pylint: disable=broad-except
                            raise ValueError(
                                f'Invalid Variable when try '
                                f'to format the job {job.name}:{str(e)}')
                workflow.update_target_state(WorkflowState[target_state])
                db.session.flush()
                logging.info('updated workflow %d target_state to %s',
                             workflow.id, workflow.target_state)
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

        create_job_flags = data['create_job_flags']
        if create_job_flags:
            jobs = workflow.get_jobs()
            if len(create_job_flags) != len(jobs):
                raise InvalidArgumentException(
                    details='Number of job defs does not match number '
                            f'of create_job_flags {len(jobs)} '
                            f'vs {len(create_job_flags)}')
            workflow.set_create_job_flags(create_job_flags)
            flags = workflow.get_create_job_flags()
            for i, job in enumerate(jobs):
                if job.workflow_id == workflow.id:
                    job.is_disabled = flags[i] == \
                                      common_pb2.CreateJobFlag.DISABLED

        db.session.commit()
        scheduler.wakeup(workflow.id)
        return {'data': workflow.to_dict()}, HTTPStatus.OK


class PeerWorkflowsApi(Resource):
    @jwt_required()
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

    @jwt_required()
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
