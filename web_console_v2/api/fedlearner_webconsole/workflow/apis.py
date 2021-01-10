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
from http import HTTPStatus
from flask_restful import Resource, reqparse
from google.protobuf.json_format import MessageToDict
from fedlearner_webconsole.workflow.models import (
    Workflow, WorkflowState, TransactionState
)
from fedlearner_webconsole.workflow_template.apis import \
    dict_to_workflow_definition
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (
    NotFoundException, ResourceConflictException, InvalidArgumentException)
from fedlearner_webconsole.scheduler.scheduler import scheduler
from fedlearner_webconsole.rpc.client import RpcClient


def _get_workflow(workflow_id):
    result = Workflow.query.filter_by(id=workflow_id).first()
    if result is None:
        raise NotFoundException()
    return result


class WorkflowsApi(Resource):
    def get(self):
        return {'data': [row.to_dict() for row in
                         Workflow.query.all()]}, HTTPStatus.OK

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
                            help='forkable is empty')
        parser.add_argument('comment')
        data = parser.parse_args()

        name = data['name']
        if Workflow.query.filter_by(name=name).first() is not None:
            raise ResourceConflictException(
                'Workflow {} already exists.'.format(name))

        # form to proto buffer
        template_proto = dict_to_workflow_definition(data['config'])
        workflow = Workflow(name=name, comment=data['comment'],
                            project_id=data['project_id'],
                            forkable=data['forkable'],
                            forked_from=data['forked_from'],
                            state=WorkflowState.NEW,
                            target_state=WorkflowState.READY,
                            transaction_state=TransactionState.READY)
        workflow.set_config(template_proto)
        db.session.add(workflow)
        db.session.commit()
        logging.info('Inserted a workflow to db')
        scheduler.wakeup(workflow.id)
        return {'data': workflow.to_dict()}, HTTPStatus.CREATED


class WorkflowApi(Resource):
    def get(self, workflow_id):
        workflow = _get_workflow(workflow_id)
        return {'data': workflow.to_dict()}, HTTPStatus.OK

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
        logging.info('update workflow %d target_state to %s',
                     workflow.id, workflow.target_state)
        return {'data': workflow.to_dict()}, HTTPStatus.OK

    def patch(self, workflow_id):
        parser = reqparse.RequestParser()
        parser.add_argument('target_state', type=str, required=True,
                            help='target_state is empty')
        target_state = parser.parse_args()['target_state']

        workflow = _get_workflow(workflow_id)
        try:
            workflow.update_target_state(WorkflowState[target_state])
            db.session.commit()
            logging.info('updated workflow %d target_state to %s',
                         workflow.id, workflow.target_state)
            scheduler.wakeup(workflow.id)
        except ValueError as e:
            raise InvalidArgumentException(details=str(e)) from e
        return {'data': workflow.to_dict()}, HTTPStatus.OK


class PeerWorkflowsApi(Resource):
    def get(self, workflow_id):
        # TODO: get jobs details

        workflow = _get_workflow(workflow_id)
        project_config = workflow.project.get_config()
        peer_workflows = {}
        for party in project_config.participants:
            client = RpcClient(project_config, party)
            resp = client.get_workflow(workflow.name)
            peer_workflows[party.name] = MessageToDict(
                resp,
                preserving_proto_field_name=True,
                including_default_value_fields=True)
        return {'data': {'self': workflow.to_dict(),
                         'peers': peer_workflows}}, HTTPStatus.OK


def initialize_workflow_apis(api):
    api.add_resource(WorkflowsApi, '/workflows')
    api.add_resource(WorkflowApi, '/workflows/<int:workflow_id>')
    api.add_resource(PeerWorkflowsApi,
                     '/workflows/<int:workflow_id>/peer_workflows')
