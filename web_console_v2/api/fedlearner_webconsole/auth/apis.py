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
from flask_jwt_extended import jwt_required, create_access_token

from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.exceptions import (
    NotFoundException, InvalidArgumentException,
    ResourceConflictException, UnauthorizedException)

class SigninApi(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True, help='username is empty')
        parser.add_argument('password', required=True, help='password is empty')
        data = parser.parse_args()
        username = data['username']
        password = data['password']

        user = User.query.filter_by(username=username).first()
        if user is None:
            raise NotFoundException()
        if not user.verify_password(password):
            raise UnauthorizedException('Invalid password')
        token = create_access_token(identity=username)
        return {'id': user.id, 'access_token': token}, HTTPStatus.OK


class UsersApi(Resource):
    @jwt_required()
    def get(self):
        return {'data': [row.to_dict() for row in User.query.all()]}

    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True, help='username is empty')
        parser.add_argument('password', required=True, help='password is empty')
        data = parser.parse_args()
        username = data['username']
        password = data['password']

        if User.query.filter_by(username=username).first() is not None:
            raise ResourceConflictException(
                'user {} already exists'.format(username))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return {'id': user.id, 'username': user.username}, HTTPStatus.CREATED


class UserApi(Resource):
    def _find_user(self, user_id):
        user = User.query.filter_by(id=user_id).first()
        if user is None:
            raise NotFoundException()
        return user

    @jwt_required()
    def get(self, user_id):
        user = self._find_user(user_id)
        return user.to_dict(), HTTPStatus.OK

    @jwt_required()
    def put(self, user_id):
        user = self._find_user(user_id)
        data = request.get_json()
        new_password = data.pop('new_password', None)
        if new_password:
            old_password = data.pop('old_password', None)

        if data:
            details = {}
            for key in data.keys():
                details[key] = 'Invalid field'
            raise InvalidArgumentException(details=details)

        if new_password:
            if not user.verify_password(old_password):
                raise UnauthorizedException(message='Wrong old password')
            user.set_password(new_password)

        db.session.commit()
        return {'username': user.username}, HTTPStatus.OK

    @jwt_required()
    def delete(self, user_id):
        user = self._find_user(user_id)
        db.session.delete(user)
        db.session.commit()
        return {'username': user.username}, HTTPStatus.OK


def initialize_auth_apis(api):
    api.add_resource(SigninApi, '/auth/signin')
    api.add_resource(UsersApi, '/auth/users')
    api.add_resource(UserApi, '/auth/users/<int:user_id>')
