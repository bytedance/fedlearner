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

# coding: utf-8
# pylint: disable=cyclic-import
from uuid import uuid4
from http import HTTPStatus
import logging
from flask_restful import Resource, abort, reqparse
from fedlearner_webconsole.workflow.models import Workflow, WorkflowStatus
from fedlearner_webconsole.template.apis import dict_to_workflow_definition, check_group_match
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.grpc_apis import WorkflowGrpc
workflow_mutex = {}
workflow_grpc = WorkflowGrpc()


def get_workflow(workflow_id):
    result = Workflow.query.filter_by(id=workflow_id).first()
    if result is None:
        abort(HTTPStatus.BAD_REQUEST,
              msg='The workflow is not existed')
    return result


def lock_workflow(workflow, prepare_status):
    if workflow.uid in workflow_mutex and workflow_mutex[workflow.uid]:
        abort(HTTPStatus.CONFLICT,
              msg='The workflow status is being modified')
    if workflow.status not in prepare_status:
        abort(HTTPStatus.BAD_REQUEST,
              msg='The workflow status is wrong')
    workflow_mutex[workflow.uid] = True


def release_workflow(workflow):
    workflow_mutex[workflow.uid] = False


class WorkflowListApi(Resource):
    def get(self):
        return {'data': [row.to_dict() for row in Workflow.query.all()]}, HTTPStatus.OK

    def post(self):

        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, help='name is empty')
        parser.add_argument('comment')
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('peer_forkable', type=bool, required=True, help='peer_forkable is empty')
        parser.add_argument('project_token', required=True, help='project_token is empty')
        data = parser.parse_args()
        name = data['name']
        comment = data['comment']
        config = data['config']
        peer_forkable = data['peer_forkable']
        project_token = data['project_token']

        if Workflow.query.filter_by(name=name).first() is not None:
            abort(HTTPStatus.CONFLICT,
                  msg='workflow %s already exists' % name)
        # form to proto buffer
        template_proto = dict_to_workflow_definition(config)
        uuid = uuid4().hex
        workflow = Workflow(name=name, comment=comment,
                            group_alias=template_proto.group_alias,
                            peer_forkable=peer_forkable, project_token=project_token,
                            uid=uuid, status=WorkflowStatus.CREATE_PREPARE_SENDER)
        workflow.set_config(template_proto)
        db.session.add(workflow)
        db.session.commit()
        logging.info('Inserted a workflow to db')
        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


class WorkflowApi(Resource):
    def get(self, workflow_id):
        result = get_workflow(workflow_id)
        return {'data': result.to_dict()}, HTTPStatus.OK


class WorkflowCreateApi(Resource):
    def patch(self, workflow_id):
        workflow = get_workflow(workflow_id)
        lock_workflow(workflow, [WorkflowStatus.CREATE_PREPARE_SENDER])
        workflow.status = WorkflowStatus.CREATE_COMMITTABLE_SENDER
        # TODO: filter the config only send readable and writeable Variables
        try:
            workflow_grpc.create_workflow(workflow.uid, workflow.name, workflow.config,
                                          workflow.project_token, workflow.peer_forkable)
        # TODO: specify the exception class
        except:
            db.session.rollback()
            release_workflow(workflow)
            abort(HTTPStatus.INTERNAL_SERVER_ERROR,
                  msg='Sending failed')
        db.session.commit()
        logging.info('update workflow %d status to CREATE_COMMITTABLE_SENDER' % workflow.id)
        release_workflow(workflow)
        return {'data': workflow.to_dict()}, HTTPStatus.OK


class WorkflowUpdateApi(Resource):
    def put(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('comment')
        parser.add_argument('peer_forkable', required=True, help='peer_forkable is empty')
        parser.add_argument('config', type=dict, required=True, help='config is empty')
        data = parser.parse_args()
        comment = data['comment']
        peer_forkable = data['peer_forkable']
        config = data['config']
        workflow = get_workflow(workflow_id)
        lock_workflow(workflow, [WorkflowStatus.CREATE_PREPARE_RECEIVER])
        workflow.set_config(dict_to_workflow_definition(config))
        workflow.comment = comment
        workflow.peer_forkable = peer_forkable
        workflow.status = WorkflowStatus.CREATE_COMMITTABLE_RECEIVER
        db.session.commit()
        logging.info('update workflow %d status to %s' % workflow.id % workflow.status)
        release_workflow(workflow)
        return {'data': workflow.to_dict()}, HTTPStatus.OK

    def patch(self, workflow_id):
        workflow = get_workflow(workflow_id)
        lock_workflow(workflow, [WorkflowStatus.CREATE_COMMITTABLE_RECEIVER])
        workflow.status = WorkflowStatus.CREATED
        # TODO: filter the config only send readable and writeable Variables
        try:
            workflow_grpc.confirm_workflow(workflow.uid, workflow.config,
                                           workflow.project_token, workflow.peer_forkable)
        # TODO: specify the exception class
        except:
            db.session.rollback()
            release_workflow(workflow)
            abort(HTTPStatus.INTERNAL_SERVER_ERROR,
                  msg='Sending failed')
        db.session.commit()
        logging.info('update workflow %d status to %s' % workflow.id % workflow.status)
        release_workflow(workflow)
        return {'data': workflow.to_dict()}, HTTPStatus.OK


class WorkflowForkApi(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('origin_id', required=True, help='origin_id is empty')
        parser.add_argument('name', required=True, help='name is empty')
        parser.add_argument('comment')
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        parser.add_argument('peer_config', type=dict)
        parser.add_argument('project_token', required=True, help='project_token is empty')
        data = parser.parse_args()
        origin_id = data['origin_id']
        origin_workflow = get_workflow(origin_id)
        lock_workflow(origin_workflow, [WorkflowStatus.CREATED])
        release_workflow(origin_workflow)
        name = data['name']
        comment = data['comment']
        config = data['config']
        project_token = data['project_token']
        peer_config = data['peer_config']
        if Workflow.query.filter_by(name=name).first() is not None:
            abort(HTTPStatus.CONFLICT,
                  msg='workflow %s already exists' % name)
        # form to proto buffer
        template_proto = dict_to_workflow_definition(config)
        peer_template_proto = dict_to_workflow_definition(peer_config)

        # check if fork from orgin
        if (not check_group_match(template_proto, origin_workflow.get_config, True)) and (
             not check_group_match(peer_template_proto, origin_workflow.get_peer_config, True)):
            abort(HTTPStatus.BAD_REQUEST,
                  msg='wrong config form')

        uuid = uuid4().hex
        workflow = Workflow(name=name, comment=comment,
                            group_alias=template_proto.group_alias, forkable=False,
                            peer_forkable=False, project_token=project_token,
                            uid=uuid, status=WorkflowStatus.FORK_SENDER)
        workflow.set_config(template_proto)
        workflow.set_peer_config(peer_template_proto)
        db.session.add(workflow)
        db.session.commit()
        logging.info('Fork a workflow %s to db' % workflow.name)
        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


class WorkflowForkSend(Resource):
    def patch(self, workflow_id):
        workflow = get_workflow(workflow_id)
        lock_workflow(workflow, [WorkflowStatus.FORK_SENDER])
        workflow.status = WorkflowStatus.CREATED
        # TODO: filter the config only send readable and writeable Variables
        try:
            workflow_grpc.fork_workflow(workflow.uid, workflow.name, workflow.project_token
                                        , workflow.config, workflow.peer_config)
        # TODO: specify the exception class
        except:
            db.session.rollback()
            release_workflow(workflow)
            abort(HTTPStatus.INTERNAL_SERVER_ERROR,
                  msg='Sending failed')
        db.session.commit()
        logging.info('update workflow %d status to %s' % workflow.id % workflow.status)
        release_workflow(workflow)
        return {'data': workflow.to_dict()}, HTTPStatus.OK


def initialize_workflow_apis(api):
    api.add_resource(WorkflowListApi, '/workflows')
    api.add_resource(WorkflowApi, '/workflows/<int:workflow_id>')
    api.add_resource(WorkflowCreateApi, '/workflows/create/<int:workflow_id>')
    api.add_resource(WorkflowUpdateApi, '/workflows/update/<int:workflow_id>')
    api.add_resource(WorkflowForkApi, '/workflows/fork')
    api.add_resource(WorkflowForkSend, '/workflows/fork/<int:workflow_id>')

