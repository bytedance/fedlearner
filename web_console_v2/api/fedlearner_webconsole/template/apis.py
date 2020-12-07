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
from flask import request
from flask_restful import Resource, abort
from google.protobuf.json_format import ParseDict, ParseError
from fedlearner_webconsole.template.models import Template
from fedlearner_webconsole.proto import template_pb2
from fedlearner_webconsole.db import db


class TemplateListApi(Resource):
    def get(self):
        return {'data': [row.get_title() for row in Template.query.all()]}

    def post(self):
        try:
            data = request.json
            if data is None:
                abort(HTTPStatus.BAD_REQUEST, msg='json parsing failed')
            name = data.get('name')
            if name is None:
                abort(HTTPStatus.BAD_REQUEST, msg='name is empty')
            if Template.query.filter_by(name=name).first() is not None:
                abort(HTTPStatus.CONFLICT,
                      msg='template %s already exists' % name)
            comment = data.get('comment')
            config = data.get('config')
            if config is None:
                abort(HTTPStatus.BAD_REQUEST, msg='config is empty')
            # form to proto buffer
            template_proto = template_pb2.Template()
            template_proto = ParseDict(config, template_proto)
            template = Template(name=name, comment=comment,
                                group_alias=template_proto.group_alias)
            template.set_config(template_proto)
            db.session.add(template)
            db.session.commit()
        except ParseError:
            abort(HTTPStatus.BAD_REQUEST, msg='wrong template form')


class TemplateApi(Resource):
    def get(self, template_id):
        return {'data': Template.query.filter_by(id=template_id).
            first().to_dict()}


def initialize_template_apis(api):
    api.add_resource(TemplateListApi, '/template')
    api.add_resource(TemplateApi, '/template/<int:template_id>')
