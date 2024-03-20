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
# pylint: disable=cyclic-import
import re
import datetime
from http import HTTPStatus
from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended.utils import get_current_user
from flask_jwt_extended import create_access_token, decode_token, get_jwt

from fedlearner_webconsole.utils.base64 import base64decode
from fedlearner_webconsole.utils.decorators import jwt_required

from fedlearner_webconsole.utils.decorators import admin_required
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import (State, User, Role,
                                               MUTABLE_ATTRS_MAPPER, Session)
from fedlearner_webconsole.exceptions import (NotFoundException,
                                              InvalidArgumentException,
                                              ResourceConflictException,
                                              UnauthorizedException,
                                              NoAccessException)

# rule: password must have a letter, a num and a special character
PASSWORD_FORMAT_L = re.compile(r'.*[A-Za-z]')
PASSWORD_FORMAT_N = re.compile(r'.*[0-9]')
PASSWORD_FORMAT_S = re.compile(r'.*[`!@#$%^&*()\-_=+|{}\[\];:\'\",<.>/?~]')


def check_password_format(password: str):
    if not 8 <= len(password) <= 20:
        raise InvalidArgumentException(
            'Password is not legal: 8 <= length <= 20')
    required_chars = []
    if PASSWORD_FORMAT_L.match(password) is None:
        required_chars.append('a letter')
    if PASSWORD_FORMAT_N.match(password) is None:
        required_chars.append('a num')
    if PASSWORD_FORMAT_S.match(password) is None:
        required_chars.append('a special character')
    if required_chars:
        tip = ', '.join(required_chars)
        raise InvalidArgumentException(
            f'Password is not legal: must have {tip}.')


class SigninApi(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username',
                            required=True,
                            help='username is empty')
        parser.add_argument('password',
                            required=True,
                            help='password is empty')
        data = parser.parse_args()
        username = data['username']
        password = base64decode(data['password'])
        user = User.query.filter_by(username=username).filter_by(
            state=State.ACTIVE).first()
        if user is None:
            raise NotFoundException(f'Failed to find user: {username}')
        if not user.verify_password(password):
            raise UnauthorizedException('Invalid password')
        token = create_access_token(identity=username)
        decoded_token = decode_token(token)

        session = Session(jti=decoded_token.get('jti'),
                          expired_at=datetime.datetime.fromtimestamp(
                              decoded_token.get('exp')))
        db.session.add(session)
        db.session.commit()

        return {
                   'data': {
                       'user': user.to_dict(),
                       'access_token': token
                   }
               }, HTTPStatus.OK

    @jwt_required()
    def delete(self):
        decoded_token = get_jwt()

        jti = decoded_token.get('jti')
        Session.query.filter_by(jti=jti).delete()
        db.session.commit()

        return {}, HTTPStatus.OK


class UsersApi(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        return {
            'data': [
                row.to_dict()
                for row in User.query.filter_by(state=State.ACTIVE).all()
            ]
        }

    @jwt_required()
    @admin_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username',
                            required=True,
                            help='username is empty')
        parser.add_argument('password',
                            required=True,
                            help='password is empty')
        parser.add_argument('role', required=True, help='role is empty')
        parser.add_argument('name', required=True, help='name is empty')
        parser.add_argument('email', required=True, help='email is empty')

        data = parser.parse_args()
        username = data['username']
        password = base64decode(data['password'])
        role = data['role']
        name = data['name']
        email = data['email']

        check_password_format(password)

        if User.query.filter_by(username=username).first() is not None:
            raise ResourceConflictException(
                'user {} already exists'.format(username))
        user = User(username=username,
                    role=role,
                    name=name,
                    email=email,
                    state=State.ACTIVE)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return {'data': user.to_dict()}, HTTPStatus.CREATED


class UserApi(Resource):
    def _find_user(self, user_id) -> User:
        user = User.query.filter_by(id=user_id).first()
        if user is None or user.state == State.DELETED:
            raise NotFoundException(
                f'Failed to find user_id: {user_id}')
        return user

    def _check_current_user(self, user_id, msg):
        current_user = get_current_user()
        if not current_user.role == Role.ADMIN \
                and not user_id == current_user.id:
            raise NoAccessException(msg)

    @jwt_required()
    def get(self, user_id):
        self._check_current_user(user_id,
                                 'user cannot get other user\'s information')
        user = self._find_user(user_id)
        return {'data': user.to_dict()}, HTTPStatus.OK

    @jwt_required()
    def patch(self, user_id):
        self._check_current_user(user_id,
                                 'user cannot modify other user\'s information')
        user = self._find_user(user_id)

        mutable_attrs = MUTABLE_ATTRS_MAPPER.get(get_current_user().role)

        data = request.get_json()
        for k, v in data.items():
            if k not in mutable_attrs:
                raise InvalidArgumentException(f'cannot edit {k} attribute!')
            if k == 'password':
                password = base64decode(v)
                check_password_format(password)
                user.set_password(password)
            else:
                setattr(user, k, v)

        db.session.commit()
        return {'data': user.to_dict()}, HTTPStatus.OK

    @jwt_required()
    @admin_required
    def delete(self, user_id):
        user = self._find_user(user_id)

        current_user = get_current_user()
        if current_user.id == user_id:
            raise InvalidArgumentException('cannot delete yourself')

        user.state = State.DELETED
        db.session.commit()
        return {'data': user.to_dict()}, HTTPStatus.OK


def initialize_auth_apis(api):
    api.add_resource(SigninApi, '/auth/signin')
    api.add_resource(UsersApi, '/auth/users')
    api.add_resource(UserApi, '/auth/users/<int:user_id>')
