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
from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db



class TemplateListApi(Resource):
    def get(self):
        return {'data': [row.to_dict() for row in Template.query.all()]}

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
        print(config)
        print(config)
        if Template.query.filter_by(name=name).first() is not None:
            abort(HTTPStatus.CONFLICT,
                  msg='template %s already exists' % name)
        # form to proto buffer
        template_proto = workflow_definition_pb2.WorkflowDefinition()
        try:
            template_proto = ParseDict(config, template_proto)
        except ParseError:
            abort(HTTPStatus.BAD_REQUEST, msg='wrong template form')
        template = Template(name=name, comment=comment,
                            group_alias=template_proto.group_alias)
        template.set_config(template_proto)
        db.session.add(template)
        db.session.commit()
        logging.info('Inserted a template to db')
        return {'group_alias': template.group_alias}, HTTPStatus.OK


class TemplateApi(Resource):
    def get(self, template_id):
        result = Template.query.filter_by(id=template_id).first()
        if result is None:
            abort(HTTPStatus.BAD_REQUEST,
                  msg='The template is not existed')
        return {'data': result.to_dict()}

# TODO: fork method to get templates by workflowid


def initialize_template_apis(api):
    api.add_resource(TemplateListApi, '/workflow_templates')
    api.add_resource(TemplateApi, '/workflow_templates/<int:template_id>')
