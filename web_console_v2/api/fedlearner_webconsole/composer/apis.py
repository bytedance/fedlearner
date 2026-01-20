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

from flask_restful import Resource, Api
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.models import ItemStatus, SchedulerItem
from fedlearner_webconsole.composer.composer_service import SchedulerItemService, SchedulerRunnerService
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required
from fedlearner_webconsole.utils.flask_utils import make_flask_response, FilterExpField
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException
from webargs.flaskparser import use_kwargs, use_args
from marshmallow import Schema, fields, validate


class ListSchedulerItemsParams(Schema):
    filter = FilterExpField(required=False, load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)


class ListSchedulerRunnersParams(Schema):
    filter = FilterExpField(required=False, load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)


class SchedulerItemsApi(Resource):

    @credentials_required
    @admin_required
    @use_args(ListSchedulerItemsParams(), location='query')
    def get(self, params: dict):
        """Get a list of all scheduler items.
        ---
        tags:
          - composer
        description: Get a list of all scheduler items.
        parameters:
        - in: query
          name: filter
          schema:
            type: string
          required: false
        - in: query
          name: page
          schema:
            type: integer
          required: false
        - in: query
          name: page_size
          schema:
            type: integer
          required: false
        responses:
          200:
            description: Get a list of all scheduler items result
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.SchedulerItemPb'
        """
        with db.session_scope() as session:
            try:
                pagination = SchedulerItemService(session).get_scheduler_items(
                    filter_exp=params['filter'],
                    page=params['page'],
                    page_size=params['page_size'],
                )
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            data = [t.to_proto() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())


class SchedulerItemApi(Resource):

    @credentials_required
    @admin_required
    @use_args(ListSchedulerRunnersParams(), location='query')
    def get(self, params: dict, item_id: int):
        """Get all scheduler runners by item_id
        ---
        tags:
          - composer
        description: Get all scheduler runners by item_id
        parameters:
        - in: path
          name: item_id
          schema:
            type: integer
          required: true
          description: The ID of the scheduler item.
        - in: query
          name: filter
          schema:
            type: string
          required: false
        - in: query
          name: page
          schema:
            type: integer
          required: false
        - in: query
          name: page_size
          schema:
            type: integer
          required: false
        responses:
          200:
            description: Get all scheduler runners by item_id
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.SchedulerRunnerPb'
        """
        with db.session_scope() as session:
            try:
                pagination = SchedulerRunnerService(session).get_scheduler_runners(filter_exp=params['filter'],
                                                                                   item_id=item_id,
                                                                                   page=params['page'],
                                                                                   page_size=params['page_size'])
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            data = [t.to_proto() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @credentials_required
    @admin_required
    @use_kwargs(
        {'status': fields.Str(required=True, validate=validate.OneOf([ItemStatus.ON.name, ItemStatus.OFF.name]))},
        location='json')
    def patch(self, item_id: int, status: str):
        """Change status of a scheduler item
          ---
          tags:
            - composer
          description: change SchedulerItem status
          parameters:
          - in: path
            required: true
            name: item_id
            schema:
              type: integer
            required: false
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    status:
                      type: string
          responses:
            200:
              description: The SchedulerItem's status has been updated
              content:
                application/json:
                  schema:
                      $ref: '#/definitions/fedlearner_webconsole.proto.SchedulerItemPb'
            400:
              description: The param of state in the request body is invalid
            404:
              description: The scheduleritem with specified ID is not found
        """
        with db.session_scope() as session:
            scheduler_item = session.query(SchedulerItem).filter_by(id=item_id).first()
            if not scheduler_item:
                raise NotFoundException(f'Failed to find scheduler_item: {item_id}')
            try:
                scheduler_item.status = ItemStatus[status].value
                session.commit()
            except ValueError as e:
                raise InvalidArgumentException(f'Invalid argument for Status: {status}') from e
            return make_flask_response(scheduler_item.to_proto())


class SchedulerRunnersApi(Resource):

    @credentials_required
    @admin_required
    @use_args(ListSchedulerRunnersParams(), location='query')
    def get(self, params: dict):
        """Get a list of all scheduler runners
        ---
        tags:
          - composer
        description: get scheduler runners list
        parameters:
        - in: query
          name: filter
          schema:
            type: string
          required: false
        - in: query
          name: page
          schema:
            type: integer
          required: false
        - in: query
          name: page_size
          schema:
            type: integer
          required: false
        responses:
          200:
            description: Get scheduler runners list result
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.SchedulerRunnerPb'
        """
        with db.session_scope() as session:
            try:
                pagination = SchedulerRunnerService(session).get_scheduler_runners(filter_exp=params['filter'],
                                                                                   page=params['page'],
                                                                                   page_size=params['page_size'])
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            data = [t.to_proto() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())


def initialize_composer_apis(api: Api):
    api.add_resource(SchedulerItemsApi, '/scheduler_items')
    api.add_resource(SchedulerItemApi, '/scheduler_items/<int:item_id>')
    api.add_resource(SchedulerRunnersApi, '/scheduler_runners')
