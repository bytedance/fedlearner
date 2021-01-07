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
from http import HTTPStatus
import logging
from flask_restful import Resource, reqparse, request
from google.protobuf.json_format import ParseDict, ParseError
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (
    NotFoundException, InvalidArgumentException,
    ResourceConflictException)


def check_group_same(config_a, config_b):
    """
    Checks two workflow definitions are same or
    not from federated job perspective.
    """
    job_dict_a = {}
    job_dict_b = {}
    for job in config_a.job_definitions:
        if job.is_federated:
            job_dict_a[job.name] = job.is_left
    for job in config_b.job_definitions:
        if job.is_federated:
            job_dict_b[job.name] = job.is_left
    return job_dict_a == job_dict_b


def check_group_match(config_a, config_b):
    """
    Checks two workflow definitions are match
     or not from federated job perspective.
    """
    job_dict_a = {}
    job_dict_b = {}
    for job in config_a.job_definitions:
        if job.is_federated:
            job_dict_a[job.name] = job.is_left
    for job in config_b.job_definitions:
        if job.is_federated:
            job_dict_b[job.name] = not job.is_left
    return job_dict_a == job_dict_b


def dict_to_workflow_definition(config):
    try:
        template_proto = ParseDict(config,
                                   workflow_definition_pb2.WorkflowDefinition())
        return template_proto
    except ParseError as e:
        raise InvalidArgumentException(details=str(e)) from e


class WorkflowTemplatesApi(Resource):
    def _get_match_templates(self, workflow_id):
        """
        find templates which match the peer's config.
        """
        workflow = Workflow.query.filter_by(id=workflow_id).first()
        if workflow is None:
            raise NotFoundException()
        templates = WorkflowTemplate.query.filter_by(
            group_alias=workflow.group_alias)
        result = []
        for template in templates:
            if check_group_match(template.get_config(),
                                 workflow.get_peer_config):
                result.append(template.to_dict())
        return {'data': result}, HTTPStatus.OK

    def get(self):
        if 'workflow_id' in request.args:
            return self._get_match_templates(request.args['workflow_id'])
        return {'data': [row.to_dict() for row in
                         WorkflowTemplate.query.all()]}, HTTPStatus.OK

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, help='name is empty')
        parser.add_argument('comment')
        parser.add_argument('config', type=dict, required=True,
                            help='config is empty')
        data = parser.parse_args()
        name = data['name']
        comment = data['comment']
        config = data['config']
        if WorkflowTemplate.query.filter_by(name=name).first() is not None:
            raise ResourceConflictException(
                'Workflow template {} already exists'.format(name))
        # form to proto buffer
        template_proto = dict_to_workflow_definition(config)
        group_template = WorkflowTemplate.query.filter_by(
            group_alias=template_proto.group_alias).first()
        if group_template is not None:
            group_proto = group_template.get_config()
            if not (check_group_match(group_proto, template_proto) or
                    check_group_same(group_proto, template_proto)):
                raise InvalidArgumentException(
                    'The group is not matched with existing groups.')
        template = WorkflowTemplate(name=name, comment=comment,
                                    group_alias=template_proto.group_alias)
        template.set_config(template_proto)
        db.session.add(template)
        db.session.commit()
        logging.info('Inserted a workflow_template to db')
        return {'data': template.to_dict()}, HTTPStatus.CREATED


class WorkflowTemplateApi(Resource):
    def get(self, template_id):
        result = WorkflowTemplate.query.filter_by(id=template_id).first()
        if result is None:
            raise NotFoundException()
        return {'data': result.to_dict()}, HTTPStatus.OK


def initialize_workflow_template_apis(api):
    api.add_resource(WorkflowTemplatesApi, '/workflow_templates')
    api.add_resource(WorkflowTemplateApi,
                     '/workflow_templates/<int:template_id>')
