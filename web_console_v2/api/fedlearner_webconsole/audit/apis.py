#  Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  coding: utf-8
from http import HTTPStatus
from typing import Optional

from flask_restful import Api, Resource
from marshmallow import fields, validate
from webargs.flaskparser import use_kwargs
from dateutil.relativedelta import relativedelta
from fedlearner_webconsole.audit.models import EventType
from fedlearner_webconsole.audit.services import EventService
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.flask_utils import make_flask_response
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.utils.pp_datetime import to_timestamp, now
from fedlearner_webconsole.utils.filtering import parse_expression


class EventsApi(Resource):

    @credentials_required
    @admin_required
    @use_kwargs(
        {
            'filter_exp': fields.String(validate=validate.Length(min=1), data_key='filter', load_default=None),
            'page': fields.Integer(load_default=1),
            'page_size': fields.Integer(load_default=10)
        },
        location='query')
    def get(self, filter_exp: Optional[str], page: int, page_size: int):
        """Get audit events
        ---
        tags:
          - audit
        description: get audit events
        parameters:
          - name: filter
            in: query
            schema:
              type: string
          - name: page
            in: query
            schema:
              type: integer
          - name: page_size
            in: query
            schema:
              type: integer
        responses:
          200:
            description: Events are returned
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.Event'
        """
        with db.session_scope() as session:
            if filter_exp is not None:
                filter_exp = parse_expression(filter_exp)
            query = EventService(session).get_events(filter_exp)
            pagination = paginate(query, page, page_size)
            data = [model.to_proto() for model in pagination.get_items()]
            return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @credentials_required
    @admin_required
    @use_kwargs({'event_type': fields.String(required=True, validate=validate.OneOf([a.name for a in EventType]))},
                location='query')
    def delete(self, event_type: str):
        """Delete audit events that are older than 6 months
        ---
        tags:
          - audit
        parameters:
          - name: event_type
            in: query
            schema:
              type: string
        responses:
          204:
            description: Events are deleted successfully
        """
        end_time = to_timestamp(now() - relativedelta(months=6))
        if EventType[event_type] == EventType.RPC:
            filter_exp = parse_expression(f'(and(start_time>0)(end_time<{end_time})(source:["RPC"]))')
        elif EventType[event_type] == EventType.USER_ENDPOINT:  # delete API/UI events
            filter_exp = parse_expression(
                f'(and(start_time>0)(end_time<{end_time})(source:["UNKNOWN_SOURCE","UI","API"]))')
        with db.session_scope() as session:
            EventService(session).delete_events(filter_exp)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


def initialize_audit_apis(api: Api):
    api.add_resource(EventsApi, '/events')
