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
from flask_restful import Resource, reqparse
from flask_jwt_extended.utils import get_current_user
from flask_jwt_extended import create_access_token
from fedlearner_webconsole.utils.decorators import jwt_required

from fedlearner_webconsole.utils.decorators import admin_required
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import (State, User, Role,
                                               MUTABLE_ATTRS_MAPPER)
from fedlearner_webconsole.exceptions import (NotFoundException,
                                              InvalidArgumentException,
                                              ResourceConflictException,
                                              UnauthorizedException)


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
        password = data['password']
        user = User.query.filter_by(username=username).filter_by(
            state=State.ACTIVE).first()
        if user is None:
            raise NotFoundException()
        if not user.verify_password(password):
            raise UnauthorizedException('Invalid password')
        token = create_access_token(identity=username)
        return {
            'data': {
                'user': user.to_dict(),
                'access_token': token
            }
        }, HTTPStatus.OK


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
        password = data['password']
        role = data['role']
        name = data['name']
        email = data['email']

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
            raise NotFoundException()
        return user

    @jwt_required()
    def get(self, user_id):
        user = self._find_user(user_id)
        return {'data': user.to_dict()}, HTTPStatus.OK

    @jwt_required()
    def patch(self, user_id):
        user = self._find_user(user_id)

        current_user = get_current_user()
        if current_user.role != Role.ADMIN and current_user.id != user_id:
            raise UnauthorizedException('user cannot modify others infomation')

        mutable_attrs = MUTABLE_ATTRS_MAPPER.get(current_user.role)

        data = request.get_json()
        for k, v in data.items():
            if k not in mutable_attrs:
                raise InvalidArgumentException(f'cannot edit {k} attribute!')
            if k == 'password':
                user.set_password(v)
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
