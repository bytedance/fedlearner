# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from http import HTTPStatus
from sqlalchemy.orm import joinedload
from flask_restful import Resource
from typing import Optional
from webargs.flaskparser import use_args, use_kwargs
from marshmallow import fields, validate

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.filtering_pb2 import FilterOp
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.mmgr.models import Model, ModelJob
from fedlearner_webconsole.mmgr.service import ModelService, get_model
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.utils.flask_utils import FilterExpField, make_flask_response
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.proto.audit_pb2 import Event


class ModelsApi(Resource):
    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'group_id': SupportedField(type=FieldType.NUMBER, ops={FilterOp.EQUAL: None}),
        'algorithm_type': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
    }

    def __init__(self):
        self._filter_builder = FilterBuilder(model_class=Model, supported_fields=self.FILTER_FIELDS)

    @credentials_required
    @use_args(
        {
            'group_id':
                fields.Integer(required=False, load_default=None),
            'keyword':
                fields.String(required=False, load_default=None),
            'algorithm_type':
                fields.String(
                    required=False, load_default=None, validate=validate.OneOf([t.name for t in AlgorithmType])),
            'page':
                fields.Integer(required=False, load_default=None),
            'page_size':
                fields.Integer(required=False, load_default=None),
            'filter':
                FilterExpField(required=False, load_default=None),
        },
        location='query')
    def get(self, params: dict, project_id: int):
        """Get the list of models.
        ---
        tags:
          - mmgr
        description: Get the list of models
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: query
          name: group_id
          schema:
            type: integer
        - in: query
          name: keyword
          schema:
            type: string
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: filter
          schema:
            type: string
        responses:
          200:
            description: the list of models
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ModelPb'
        """
        with db.session_scope() as session:
            query = session.query(Model).options(
                joinedload(Model.job).load_only(Job.name, Job.workflow_id).options(
                    joinedload(Job.workflow).load_only(Workflow.name)),
                joinedload(Model.model_job).load_only(ModelJob.name))
            if project_id:
                query = query.filter_by(project_id=project_id)
            if params['group_id'] is not None:
                query = query.filter_by(group_id=params['group_id'])
            if params['keyword'] is not None:
                query = query.filter(Model.name.like(f'%{params["keyword"]}%'))
            if params['algorithm_type'] is not None:
                query = query.filter(Model.algorithm_type == AlgorithmType[params['algorithm_type']])
            if params['filter']:
                try:
                    query = self._filter_builder.build_query(query, params['filter'])
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            query = query.order_by(Model.created_at.desc())
            pagination = paginate(query, params['page'], params['page_size'])
            data = [d.to_proto() for d in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())


class ModelApi(Resource):

    @credentials_required
    def get(self, project_id: int, model_id: int):
        """Get the model.
        ---
        tags:
          - mmgr
        description: get the model.
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the model
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelPb'
        """
        with db.session_scope() as session:
            model = get_model(project_id=project_id, model_id=model_id, session=session)
            return make_flask_response(data=model.to_proto())

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL, op_type=Event.OperationType.UPDATE)
    @use_kwargs({'comment': fields.Str(required=False, load_default=None)}, location='json')
    def patch(self, comment: Optional[str], project_id: int, model_id: int):
        """Patch the model.
        ---
        tags:
          - mmgr
        description: patch the model.
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_id
          schema:
            type: integer
          required: true
        requestBody:
          required: False
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          200:
            description: detail of the model
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.ModelPb'
        """
        with db.session_scope() as session:
            model = get_model(project_id=project_id, model_id=model_id, session=session)
            if comment is not None:
                model.comment = comment
            session.commit()
            return make_flask_response(model.to_proto())

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.MODEL, op_type=Event.OperationType.DELETE)
    def delete(self, project_id: int, model_id: int):
        """Delete the model.
        ---
        tags:
          - mmgr
        decription: delete the model
        parameters:
        - in: path
          name: proejct_id
          schema:
            type: integer
          required: true
        - in: path
          name: model_id
          schema:
            type: integer
          required: true
        responses:
          204:
            description: delete the model successfully
        """
        with db.session_scope() as session:
            model = get_model(project_id=project_id, model_id=model_id, session=session)
            ModelService(session).delete(model.id)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


def initialize_mmgr_model_apis(api):
    api.add_resource(ModelsApi, '/projects/<int:project_id>/models')
    api.add_resource(ModelApi, '/projects/<int:project_id>/models/<int:model_id>')
