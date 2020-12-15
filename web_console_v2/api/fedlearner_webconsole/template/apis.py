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
from http import HTTPStatus
import logging
from flask_restful import Resource, abort, reqparse
from google.protobuf.json_format import ParseDict, ParseError
from fedlearner_webconsole.template.models import Template
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db


def check_group_match(config_a, config_b, flag):
    """
    check two WorkflowDefinition
    Args:
        config_a: WorkflowDefinition
        config_b: WorkflowDefinition
        flag: True return is_same then return is_match
    Returns:
        boolean
    """
    job_dict_a = {}
    job_dict_b = {}
    for job in config_a.job_definitions:
        if job.is_federated:
            job_dict_a[job.name] = job.is_left
    for job in config_b.job_definitions:
        if job.is_federated:
            job_dict_b[job.name] = flag ^ job.is_left
    return job_dict_a == job_dict_b

def dict_to_workflow_definition(config):
    template_proto = workflow_definition_pb2.WorkflowDefinition()
    try:
        template_proto = ParseDict(config, template_proto)
    except ParseError:
        abort(HTTPStatus.BAD_REQUEST, msg='Invalid template')
    return template_proto


class WorkflowTemplateListApi(Resource):

    def get(self):
        return {'data': [row.to_dict()
                         for row in Template.query.all()]}, HTTPStatus.OK

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
        if Template.query.filter_by(name=name).first() is not None:
            abort(HTTPStatus.CONFLICT,
                  msg='template %s already exists' % name)
        # form to proto buffer
        template_proto = dict_to_workflow_definition(config)
        group_template = Template.query.filter_by(
            group_alias=template_proto.group_alias).first()
        if group_template is not None:
            group_proto = group_template.get_config
            if not (check_group_match(group_proto, template_proto, True) or
                    check_group_match(group_proto, template_proto, False)):
                abort(HTTPStatus.BAD_REQUEST, msg='Cant match the group')
        template = Template(name=name, comment=comment,
                            group_alias=template_proto.group_alias)
        template.set_config(template_proto)
        db.session.add(template)
        db.session.commit()
        logging.info('Inserted a template to db')
        return {'data': template.to_dict()}, HTTPStatus.CREATED


class WorkflowTemplateApi(Resource):
    def get(self, template_id):
        result = Template.query.filter_by(id=template_id).first()
        if result is None:
            abort(HTTPStatus.NOT_FOUND,
                  msg='The template is not existed')
        return {'data': result.to_dict()}, HTTPStatus.OK


class WorkflowTemplateGroupApi(Resource):
    def get(self, workflow_id):
        workflow = Workflow.query.filter_by(id=workflow_id).first()
        if workflow is None:
            abort(HTTPStatus.NOT_FOUND,
                  msg='The workflow is not existed')
        templates = Template.query.filter_by(group_alias=workflow.group_alias)
        result = []
        for template in templates:
            if check_group_match(template.get_config(),
                                 workflow.get_peer_config, True):
                result.append(template.to_dict())
        return {'data': result}, HTTPStatus.OK


def initialize_workflow_template_apis(api):
    api.add_resource(WorkflowTemplateListApi, '/workflow_templates')
    api.add_resource(WorkflowTemplateApi, '/workflow_templates/<int:template_id>')
    api.add_resource(WorkflowTemplateGroupApi
                     , '/workflow_templates/creat_workflow/<int:workflow_id>')
