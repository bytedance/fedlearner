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
from uuid import uuid4
from http import HTTPStatus
import logging
from grpc import RpcError
from flask_restful import Resource, reqparse, request
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.workflow.models import Workflow, WorkflowStatus
from fedlearner_webconsole.workflow.workflow_lock import get_worklow_lock
from fedlearner_webconsole.workflow_template.apis import \
    dict_to_workflow_definition, check_group_same
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.grpc_apis import WorkflowGrpc
from fedlearner_webconsole.exceptions import (
    NotFoundException, InvalidArgumentException,
    ResourceConflictException)

workflow_grpc = WorkflowGrpc()

def _get_workflow(workflow_id):
    result = Workflow.query.filter_by(id=workflow_id).first()
    if result is None:
        raise NotFoundException()
    logging.info('%s has been loaded', result.uuid)
    return result


class WorkflowListApi(Resource):
    def get(self):
        return {'data': [row.to_dict() for row in
                         Workflow.query.all()]}, HTTPStatus.OK

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, help='name is empty')
        parser.add_argument('comment')
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('peer_forkable', type=bool, required=True,
                            help='peer_forkable is empty')
        parser.add_argument('project_id', required=True,
                            help='project_id is empty')
        data = parser.parse_args()
        name = data['name']
        comment = data['comment']
        config = data['config']
        peer_forkable = data['peer_forkable']
        project_id = data['project_id']
        if Project.query.filter_by(id=project_id).first() is None:
            raise InvalidArgumentException('project does not exist')
        if Workflow.query.filter_by(name=name).first() is not None:
            raise ResourceConflictException(
                'Workflow {} already exists.'.format(name))
        # form to proto buffer
        template_proto = dict_to_workflow_definition(config)
        uuid = uuid4().hex
        workflow = Workflow(name=name, comment=comment,
                            group_alias=template_proto.group_alias,
                            peer_forkable=peer_forkable,
                            project_id=project_id,
                            uuid=uuid,
                            status=WorkflowStatus.CREATE_SENDER_PREPARE)
        workflow.set_config(template_proto)
        db.session.add(workflow)
        db.session.commit()
        logging.info('Inserted a workflow to db')
        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


class WorkflowApi(Resource):
    def get(self, workflow_id):
        result = _get_workflow(workflow_id)
        return {'data': result.to_dict()}, HTTPStatus.OK

    def put(self, workflow_id):
        workflow_lock = get_worklow_lock()
        parser = reqparse.RequestParser()
        parser.add_argument('comment')
        parser.add_argument('peer_forkable', required=True,
                            help='peer_forkable is empty')
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        data = parser.parse_args()
        comment = data['comment']
        peer_forkable = data['peer_forkable']
        config = data['config']
        workflow = _get_workflow(workflow_id)
        workflow_lock.lock(workflow, [WorkflowStatus.CREATE_RECEIVER_PREPARE])
        workflow.set_config(dict_to_workflow_definition(config))
        workflow.comment = comment
        workflow.peer_forkable = peer_forkable
        workflow.status = WorkflowStatus.CREATE_RECEIVER_COMMITTABLE
        db.session.commit()
        logging.info('update workflow %d status to %s'
                     , workflow.id, workflow.status)
        workflow_lock.release(workflow)
        return {'data': workflow.to_dict()}, HTTPStatus.OK

    def patch(self, workflow_id):
        workflow_lock = get_worklow_lock()
        if 'workflow_status' not in request.args:
            raise InvalidArgumentException('workflow_status is empty.')
        workflow_status = int(request.args['workflow_status'])
        workflow = _get_workflow(workflow_id)
        workflow_lock.lock(workflow, [WorkflowStatus(workflow_status)])
        try:
            if WorkflowStatus(
                   workflow_status) == WorkflowStatus.CREATE_SENDER_PREPARE:
                workflow.status = WorkflowStatus.CREATE_SENDER_COMMITTABLE
                # TODO: filter the config only send readable
                #  and writeable Variables
                workflow_grpc.create_workflow(workflow.uuid,
                                              workflow.name,
                                              workflow.config,
                                              workflow.project_id,
                                              workflow.peer_forkable)
            elif WorkflowStatus(
                   workflow_status) \
                    == WorkflowStatus.CREATE_RECEIVER_COMMITTABLE:
                workflow.status = WorkflowStatus.CREATED
                # TODO: filter the config only send readable
                #  and writeable Variables
                workflow_grpc.confirm_workflow(workflow.uuid,
                                               workflow.config,
                                               workflow.project_id,
                                               workflow.peer_forkable)
            elif WorkflowStatus(workflow_status) == WorkflowStatus.FORK_SENDER:
                workflow.status = WorkflowStatus.CREATED
                # TODO: filter the config only send readable
                #  and writeable Variables
                workflow_grpc.fork_workflow(workflow.uuid,
                                            workflow.name,
                                            workflow.project_id,
                                            workflow.config,
                                            workflow.peer_config)
            else:
                db.session.rollback()
                db.session.refresh(workflow)
                workflow_lock.release(workflow)
                raise InvalidArgumentException('Wrong workflow status.')
            db.session.commit()
            logging.info('update workflow %d status to %s',
                         workflow.id, workflow.status)
            workflow_lock.release(workflow)
        # TODO: specify the exception class
        except RpcError as e:
            # https://docs.sqlalchemy.org/en/14/errors.html#error-bhk3
            db.session.rollback()
            db.session.refresh(workflow)
            workflow_lock.release(workflow)
            raise ResourceConflictException('Rpc Sending failed') from e
        return {'data': workflow.to_dict()}, HTTPStatus.OK

    def post(self, workflow_id):
        workflow_lock = get_worklow_lock()
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True,
                            help='name is empty')
        parser.add_argument('comment')
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('peer_config', type=dict)
        data = parser.parse_args()
        origin_id = workflow_id
        origin_workflow = _get_workflow(origin_id)
        workflow_lock.lock(origin_workflow, [WorkflowStatus.CREATED])
        workflow_lock.release(origin_workflow)
        name = data['name']
        comment = data['comment']
        config = data['config']
        project_id = origin_workflow.project_id
        peer_config = data['peer_config']
        if Workflow.query.filter_by(name=name).first() is not None:
            raise ResourceConflictException(
                'workflow {} already exists'.format(name))
        template_proto = dict_to_workflow_definition(config)
        peer_template_proto = dict_to_workflow_definition(peer_config)

        # check if fork from orgin
        if (not check_group_same(template_proto,
                                  origin_workflow.get_config())) and (
             not check_group_same(peer_template_proto,
                                   origin_workflow.get_peer_config())):
            raise InvalidArgumentException('wrong config form')

        uuid = uuid4().hex
        workflow = Workflow(name=name, comment=comment,
                            group_alias=template_proto.group_alias,
                            forkable=False,
                            peer_forkable=False,
                            project_id=project_id,
                            uuid=uuid, status=WorkflowStatus.FORK_SENDER)
        workflow.set_config(template_proto)
        workflow.set_peer_config(peer_template_proto)
        db.session.add(workflow)
        db.session.commit()
        logging.info('Fork a workflow %s to db', workflow.name)
        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


def initialize_workflow_apis(api):
    api.add_resource(WorkflowListApi, '/workflows')
    api.add_resource(WorkflowApi, '/workflows/<int:workflow_id>')
