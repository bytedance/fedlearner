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

# coding: utf-8

from http import HTTPStatus
from flask import request
from flask_restful import Resource
from fedlearner_webconsole.db import db_handler
from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.mmgr.models import Model, ModelType, ModelGroup
from fedlearner_webconsole.mmgr.service import ModelService
from fedlearner_webconsole.utils.decorators import jwt_required


class ModelApi(Resource):
    @jwt_required()
    def get(self, model_id):
        detail_level = request.args.get('detail_level', '')
        with db_handler.session_scope() as session:
            model_json = ModelService(session).query(model_id, detail_level)
        if not model_json:
            raise NotFoundException(
                f'Failed to find model: {model_id}')
        return {'data': model_json}, HTTPStatus.OK

    @jwt_required()
    def put(self, model_id):
        with db_handler.session_scope() as session:
            model = session.query(Model).filter_by(id=model_id).one_or_none()
            if not model:
                raise NotFoundException(
                    f'Failed to find model: {model_id}')
            model.extra = request.args.get('extra', model.extra)
            session.commit()
            return {'data': model.to_dict()}, HTTPStatus.OK

    @jwt_required()
    def delete(self, model_id):
        with db_handler.session_scope() as session:
            model = ModelService(session).drop(model_id)
            if not model:
                raise NotFoundException(
                    f'Failed to find model: {model_id}')
            return {'data': model.to_dict()}, HTTPStatus.OK


class ModelListApi(Resource):
    @jwt_required()
    def get(self):
        detail_level = request.args.get('detail_level', '')
        # TODO serialized query may incur performance penalty
        with db_handler.session_scope() as session:
            model_list = [
                ModelService(session).query(m.id, detail_level)
                for m in Model.query.filter(
                    Model.type.in_([
                        ModelType.NN_MODEL.value, ModelType.TREE_MODEL.value
                    ])).all()
            ]
        return {'data': model_list}, HTTPStatus.OK


class GroupListApi(Resource):
    @jwt_required()
    def get(self):
        group_list = [o.to_dict() for o in ModelGroup.query.all()]
        return {'data': group_list}, HTTPStatus.OK

    @jwt_required()
    def post(self):
        group = ModelGroup()

        group.name = request.args.get('name', group.name)
        group.extra = request.args.get('extra', group.extra)
        with db_handler.session_scope() as session:
            session.add(group)
            session.commit()

        return {'data': group.to_dict()}, HTTPStatus.OK


class GroupApi(Resource):
    @jwt_required()
    def patch(self, group_id):
        group = ModelGroup.query.filter_by(id=group_id).one_or_none()
        if not group:
            raise NotFoundException(
                f'Failed to find group: {group_id}')

        group.name = request.args.get('name', group.name)
        group.extra = request.args.get('extra', group.extra)
        with db_handler.session_scope() as session:
            session.add(group)
            session.commit()

        return {'data': group.to_dict()}, HTTPStatus.OK


def initialize_mmgr_apis(api):
    api.add_resource(ModelListApi, '/models')
    api.add_resource(ModelApi, '/models/<int:model_id>')

    api.add_resource(GroupListApi, '/model_groups')
    api.add_resource(GroupApi, '/model_groups/<int:group_id>')
