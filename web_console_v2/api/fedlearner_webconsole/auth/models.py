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

import enum

from passlib.apps import custom_app_context as pwd_context
from sqlalchemy.sql.schema import UniqueConstraint, Index
from sqlalchemy.sql import func

from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.db import db, default_table_args


class Role(enum.Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'


# yapf: disable
MUTABLE_ATTRS_MAPPER = {
    Role.USER: ('password', 'name', 'email'),
    Role.ADMIN: ('password', 'role', 'name', 'email')
}
# yapf: enable


class State(enum.Enum):
    ACTIVE = 'active'
    DELETED = 'deleted'


@to_dict_mixin(ignores=['password', 'state'])
class User(db.Model):
    __tablename__ = 'users_v2'
    __table_args__ = (UniqueConstraint('username',
                                       name='uniq_username'), default_table_args('This is webconsole user table'))
    id = db.Column(db.Integer, primary_key=True, comment='user id', autoincrement=True)
    username = db.Column(db.String(255), comment='unique name of user')
    password = db.Column(db.String(255), comment='user password after encode')
    role = db.Column(db.Enum(Role, native_enum=False, create_constraint=False, length=21),
                     default=Role.USER,
                     comment='role of user')
    name = db.Column(db.String(255), comment='name of user')
    email = db.Column(db.String(255), comment='email of user')
    state = db.Column(db.Enum(State, native_enum=False, create_constraint=False, length=21),
                      default=State.ACTIVE,
                      comment='state of user')
    sso_name = db.Column(db.String(255), comment='sso_name')
    last_sign_in_at = db.Column(db.DateTime(timezone=True),
                                nullable=True,
                                comment='the last time when user tries to sign in')
    failed_sign_in_attempts = db.Column(db.Integer,
                                        nullable=False,
                                        default=0,
                                        comment='failed sign in attempts since last successful sign in')

    def set_password(self, password):
        self.password = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)


@to_dict_mixin(ignores=['expired_at', 'created_at'])
class Session(db.Model):
    __tablename__ = 'session_v2'
    __table_args__ = (Index('idx_jti', 'jti'), default_table_args('This is webconsole session table'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='session id')
    jti = db.Column(db.String(64), comment='JWT jti')
    user_id = db.Column(db.Integer, nullable=False, comment='for whom the session is created')
    expired_at = db.Column(db.DateTime(timezone=True), comment='expired time, for db automatically clear')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
