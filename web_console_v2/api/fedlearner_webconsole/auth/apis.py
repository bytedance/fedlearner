# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import logging
import re
from http import HTTPStatus

from flask import request
from flask_restful import Resource
from marshmallow import Schema, post_load, fields, validate, EXCLUDE
from marshmallow.decorators import validates_schema
from webargs.flaskparser import use_args

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.auth.services import UserService, SessionService
from fedlearner_webconsole.iam.client import create_iams_for_user
from fedlearner_webconsole.proto import auth_pb2
from fedlearner_webconsole.swagger.models import schema_manager

from fedlearner_webconsole.utils.pp_base64 import base64decode
from fedlearner_webconsole.auth.third_party_sso import credentials_required, SsoHandlerFactory
from fedlearner_webconsole.utils.flask_utils import get_current_user, make_flask_response
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import (Role, MUTABLE_ATTRS_MAPPER)
from fedlearner_webconsole.exceptions import (NotFoundException, InvalidArgumentException, ResourceConflictException,
                                              NoAccessException, UnauthorizedException)
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.auth.third_party_sso import sso_info_manager

# rule: password must have a letter, a num and a special character
PASSWORD_FORMAT_L = re.compile(r'.*[A-Za-z]')
PASSWORD_FORMAT_N = re.compile(r'.*[0-9]')
PASSWORD_FORMAT_S = re.compile(r'.*[`!@#$%^&*()\-_=+|{}\[\];:\'\",<.>/?~]')


def _check_password_format(password: str):
    if not 8 <= len(password) <= 20:
        raise InvalidArgumentException('Password is not legal: 8 <= length <= 20')
    required_chars = []
    if PASSWORD_FORMAT_L.match(password) is None:
        required_chars.append('a letter')
    if PASSWORD_FORMAT_N.match(password) is None:
        required_chars.append('a num')
    if PASSWORD_FORMAT_S.match(password) is None:
        required_chars.append('a special character')
    if required_chars:
        tip = ', '.join(required_chars)
        raise InvalidArgumentException(f'Password is not legal: must have {tip}.')


class UserParameter(Schema):
    username = fields.Str(required=True)
    # Base64 encoded password
    password = fields.Str(required=True, validate=lambda x: _check_password_format(base64decode(x)))
    role = fields.Str(required=True, validate=validate.OneOf([x.name for x in Role]))
    name = fields.Str(required=True, validate=validate.Length(min=1))
    email = fields.Str(required=True, validate=validate.Email())

    @post_load
    def make_user(self, data, **kwargs):
        return auth_pb2.User(**data)


class SigninParameter(Schema):
    username = fields.String()
    password = fields.String()
    code = fields.String()
    ticket = fields.String()

    @validates_schema
    def validate_schema(self, data, **kwargs):
        del kwargs
        if data.get('username') is None and data.get('code') is None and data.get('ticket') is None:
            raise InvalidArgumentException('no credential detected')

    @post_load
    def make_proto(self, data, **kwargs):
        del kwargs
        return auth_pb2.SigninParameter(**data)


class SigninApi(Resource):

    @use_args(SigninParameter(unknown=EXCLUDE), location='json_or_form')
    def post(self, signin_parameter: auth_pb2.SigninParameter):
        """Sign in to the system
        ---
        tags:
          - auth
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/SigninParameter'
        responses:
          200:
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    access_token:
                      type: string
                    user:
                      type: object
                      properties:
                        schema:
                          $ref: '#/definitions/fedlearner_webconsole.proto.User'
        """
        sso_name = request.args.get('sso_name')
        return make_flask_response(SsoHandlerFactory.get_handler(sso_name).signin(signin_parameter))

    @credentials_required
    def delete(self):
        """Sign out from the system
        ---
        tags:
          - auth
        parameters:
        - in: header
          name: Authorization
          schema:
            type: string
          description: token used for current session
        responses:
          200:
            description: Signed out successfully
        """
        user = get_current_user()
        SsoHandlerFactory.get_handler(user.sso_name).signout()
        return make_flask_response()


class UsersApi(Resource):

    @credentials_required
    @admin_required
    def get(self):
        """Get a list of all users
        ---
        tags:
          - auth
        responses:
          200:
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.User'
        """
        with db.session_scope() as session:
            return make_flask_response(
                [row.to_dict() for row in UserService(session).get_all_users(filter_deleted=True)])

    @credentials_required
    @admin_required
    # if use_kwargs is used with explicit parameters, one has to write YAML document!
    # Param: https://swagger.io/docs/specification/2-0/describing-parameters/
    # Body: https://swagger.io/docs/specification/2-0/describing-request-body/
    # Resp: https://swagger.io/docs/specification/2-0/describing-responses/
    @use_args(UserParameter(unknown=EXCLUDE))
    @emits_event()
    def post(self, params: auth_pb2.User):
        """Create a user
        ---
        tags:
          - auth
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/UserParameter'
        responses:
          201:
            description: The user is created
            content:
              application/json:
                schema:
                  $ref: '#/definitions/UserParameter'
          409:
            description: A user with the same username exists
        """
        # Swagger will detect APIs automatically, but params/req body/resp have to be defined manually
        with db.session_scope() as session:
            user = UserService(session).get_user_by_username(params.username)
            if user is not None:
                raise ResourceConflictException(f'user {user.username} already exists')
            user = UserService(session).create_user_if_not_exists(username=params.username,
                                                                  role=Role(params.role),
                                                                  name=params.name,
                                                                  email=params.email,
                                                                  password=base64decode(params.password))
            session.commit()
            return make_flask_response(user.to_dict(), status=HTTPStatus.CREATED)


class UserApi(Resource):

    def _check_current_user(self, user_id, msg):
        current_user = get_current_user()
        if not current_user.role == Role.ADMIN \
                and not user_id == current_user.id:
            raise NoAccessException(msg)

    @credentials_required
    def get(self, user_id):
        """Get a user by id
        ---
        tags:
          - auth
        parameters:
        - in: path
          name: user_id
          schema:
            type: integer
        responses:
          200:
            description: The user is returned
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.User'
          404:
            description: The user with specified ID is not found
        """
        self._check_current_user(user_id, 'user cannot get other user\'s information')

        with db.session_scope() as session:
            user = UserService(session).get_user_by_id(user_id, filter_deleted=True)
            if user is None:
                raise NotFoundException(f'Failed to find user_id: {user_id}')
        return make_flask_response(user.to_dict())

    @credentials_required
    @emits_event()
    # Example of manually defining an API
    def patch(self, user_id):
        """Patch a user
        ---
        tags:
          - auth
        parameters:
        - in: path
          name: user_id
          required: true
          schema:
            type: integer
          description: The ID of the user
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/fedlearner_webconsole.proto.User'
        responses:
          200:
            description: The user is updated
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.User'
          404:
            description: The user is not found
          400:
            description: Attributes selected are uneditable
        """
        self._check_current_user(user_id, 'user cannot modify other user\'s information')

        with db.session_scope() as session:
            user = UserService(session).get_user_by_id(user_id, filter_deleted=True)
            if user is None:
                raise NotFoundException(f'Failed to find user_id: {user_id}')

            mutable_attrs = MUTABLE_ATTRS_MAPPER.get(get_current_user().role)

            data = request.get_json()
            for k, v in data.items():
                if k not in mutable_attrs:
                    raise InvalidArgumentException(f'cannot edit {k} attribute!')
                if k == 'password':
                    password = base64decode(v)
                    _check_password_format(password)
                    user.set_password(password)
                    SessionService(session).delete_session_by_user_id(user_id)
                elif k == 'role':
                    user.role = Role(v)
                else:
                    setattr(user, k, v)
            create_iams_for_user(user)
            session.commit()
        return make_flask_response(user.to_dict())

    @credentials_required
    @admin_required
    @emits_event()
    def delete(self, user_id):
        """Delete the user with specified ID
        ---
        tags:
          - auth
        parameters:
        - in: path
          name: user_id
          schema:
            type: integer
        responses:
          200:
            description: The user with specified ID is deleted
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.User'
          400:
            description: Cannot delete the user logged in within current session
          404:
            description: The user with specified ID is not found
        """
        with db.session_scope() as session:
            user_service = UserService(session)
            user = user_service.get_user_by_id(user_id, filter_deleted=True)

            if user is None:
                raise NotFoundException(f'Failed to find user_id: {user_id}')

            current_user = get_current_user()
            if current_user.id == user_id:
                raise InvalidArgumentException('cannot delete yourself')

            user = UserService(session).delete_user(user)
            session.commit()
        return make_flask_response(user.to_dict())


class SsoInfosApi(Resource):

    def get(self):
        """Get all available options of SSOs
        ---
        tags:
          - auth
        responses:
          200:
            description: All options are returned
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.Sso'
        """
        return make_flask_response([to_dict(sso, with_secret=False) for sso in sso_info_manager.sso_infos])


class SelfUserApi(Resource):

    @credentials_required
    def get(self):
        """Get current user
        ---
        tags:
          - auth
        responses:
          200:
            description: User logged in within current session is returned
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.User'
          400:
            description: No user is logged in within current session
        """
        user = get_current_user()
        # Defensively program for unexpected exception
        if user is None:
            logging.error('No current user.')
            raise UnauthorizedException('No current user.')
        return make_flask_response(user.to_dict())


def initialize_auth_apis(api):
    api.add_resource(SigninApi, '/auth/signin')
    api.add_resource(UsersApi, '/auth/users')
    api.add_resource(UserApi, '/auth/users/<int:user_id>')
    api.add_resource(SsoInfosApi, '/auth/sso_infos')
    api.add_resource(SelfUserApi, '/auth/self')

    # if a schema is used, one has to append it to schema_manager so Swagger knows there is a schema available
    schema_manager.append(UserParameter)
    schema_manager.append(SigninParameter)
