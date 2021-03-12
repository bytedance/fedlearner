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
import re
from http import HTTPStatus
import logging
from flask_restful import Resource, reqparse, request
from google.protobuf.json_format import ParseDict, ParseError
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (
    NotFoundException, InvalidArgumentException,
    ResourceConflictException)


def dict_to_workflow_definition(config):
    try:
        template_proto = ParseDict(config,
                                   workflow_definition_pb2.WorkflowDefinition())
        return template_proto
    except ParseError as e:
        raise InvalidArgumentException(details=str(e)) from e


def _dic_without_key(d, key):
    result = dict(d)
    del result[key]
    return result


class WorkflowTemplatesApi(Resource):
    def get(self):
        templates = WorkflowTemplate.query
        if 'group_alias' in request.args:
            templates = templates.filter_by(
                group_alias=request.args['group_alias'])
        if 'is_left' in request.args:
            is_left = request.args.get(key='is_left', type=int)
            if is_left is None:
                raise InvalidArgumentException('is_left must be 0 or 1')
            templates = templates.filter_by(is_left=is_left)
        # remove config from dicts to reduce the size of the list
        return {'data': [_dic_without_key(t.to_dict(),
                                          'config') for t in templates.all()
                         ]}, HTTPStatus.OK

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
        # TODO: format check
        if 'group_alias' not in config:
            raise InvalidArgumentException(details={
                'config.group_alias': 'config.group_alias is required'})
        if 'is_left' not in config:
            raise InvalidArgumentException(
                details={'config.is_left': 'config.is_left is required'})

        if WorkflowTemplate.query.filter_by(name=name).first() is not None:
            raise ResourceConflictException(
                'Workflow template {} already exists'.format(name))
        # form to proto buffer
        template_proto = dict_to_workflow_definition(config)
        for index, job_def in enumerate(template_proto.job_definitions):
            # pod label name must be no more than 63 characters.
            #  workflow.uuid is 20 characters, pod name suffix such as
            #  '-follower-master-0' is less than 19 characters, so the
            #  job name must be no more than 24
            if len(job_def.name) > 24:
                raise InvalidArgumentException(
                    details=
                    {'config.job_definitions'
                     : 'job_name:{} must be no more than 24 characters'})
            # limit from k8s
            if not re.match('[a-z0-9-]*', job_def.name):
                raise InvalidArgumentException(
                    details=
                    {f'config.job_definitions[{index}].job_name'
                     : 'Only letters(a-z), numbers(0-9) '
                       'and dashes(-) are supported.'})
        template = WorkflowTemplate(name=name,
                                    comment=comment,
                                    group_alias=template_proto.group_alias,
                                    is_left=template_proto.is_left)
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

    def delete(self, template_id):
        result = WorkflowTemplate.query.filter_by(id=template_id)
        if result.first() is None:
            raise NotFoundException()
        result.delete()
        db.session.commit()
        return {'data': {}}, HTTPStatus.OK

def initialize_workflow_template_apis(api):
    api.add_resource(WorkflowTemplatesApi, '/workflow_templates')
    api.add_resource(WorkflowTemplateApi,
                     '/workflow_templates/<int:template_id>')
