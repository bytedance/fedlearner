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
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required, use_args
from fedlearner_webconsole.utils.flask_utils import make_flask_response, FilterExpField
from fedlearner_webconsole.cleanup.services import CleanupService
from marshmallow import Schema, fields


class GetCleanupParams(Schema):
    filter = FilterExpField(required=False, load_default=None)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)


class CleanupsApi(Resource):

    @credentials_required
    @admin_required
    @use_args(GetCleanupParams(), location='query')
    def get(self, params: dict):
        """Get a list of all cleanups
        ---
        tags:
          - cleanup
        description: get cleanups list
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
            description: Get cleanups list result
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.CleanupPb'
        """
        with db.session_scope() as session:
            try:
                pagination = CleanupService(session).get_cleanups(
                    filter_exp=params['filter'],
                    page=params['page'],
                    page_size=params['page_size'],
                )
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            data = [t.to_proto() for t in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())


class CleanupApi(Resource):

    @credentials_required
    @admin_required
    def get(self, cleanup_id: int):
        """Get a cleanup by id
        ---
        tags:
          - cleanup
        description: get details of cleanup
        parameters:
        - in: path
          name: cleanup_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: Get details of cleanup
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.CleanupPb'
          404:
            description: The cleanup with specified ID is not found
        """
        with db.session_scope() as session:
            cleanup = CleanupService(session).get_cleanup(cleanup_id)
            return make_flask_response(cleanup)


class CleanupCancelApi(Resource):

    @credentials_required
    @admin_required
    def post(self, cleanup_id: int):
        """Get a cleanup by id
        ---
        tags:
          - cleanup
        description: change the state of cleanup
        parameters:
        - in: path
          name: cleanup_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: The Cleanup's state has been updated
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.CleanupPb'
          400:
            description: The param of state in the request body is invliad
          404:
            description: The cleanup with specified ID is not found
        """
        with db.session_scope() as session:
            cleanup = CleanupService(session).cancel_cleanup_by_id(cleanup_id)
            session.commit()
            return make_flask_response(cleanup)


def initialize_cleanup_apis(api: Api):
    api.add_resource(CleanupsApi, '/cleanups')
    api.add_resource(CleanupApi, '/cleanups/<int:cleanup_id>')
    api.add_resource(CleanupCancelApi, '/cleanups/<int:cleanup_id>:cancel')
