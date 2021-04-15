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

import enum
from passlib.apps import custom_app_context as pwd_context
from sqlalchemy.sql.schema import UniqueConstraint, Index
from sqlalchemy.sql import func

from fedlearner_webconsole.db import db, to_dict_mixin, default_table_args


class Role(enum.Enum):
    USER = 'user'
    ADMIN = 'admin'


MUTABLE_ATTRS_MAPPER = {
    Role.USER: ('password', 'name', 'email'),
    Role.ADMIN: ('password', 'role', 'name', 'email')
}


class State(enum.Enum):
    ACTIVE = 'active'
    DELETED = 'deleted'


@to_dict_mixin(ignores=['password', 'state'])
class User(db.Model):
    __tablename__ = 'users_v2'
    __table_args__ = (UniqueConstraint('username', name='uniq_username'),
                      default_table_args('This is webconsole user table'))
    id = db.Column(db.Integer, primary_key=True, comment='user id')
    username = db.Column(db.String(255), comment='unique name of user')
    password = db.Column(db.String(255), comment='user password after encode')
    role = db.Column(db.Enum(Role, native_enum=False),
                     default=Role.USER,
                     comment='role of user')
    name = db.Column(db.String(255), comment='name of user')
    email = db.Column(db.String(255), comment='email of user')
    state = db.Column(db.Enum(State, native_enum=False),
                      default=State.ACTIVE,
                      comment='state of user')

    def set_password(self, password):
        self.password = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)


class Session(db.Model):
    __tablename__ = 'session_v2'
    __table_args__ = (Index('idx_jti', 'jti'),
                      default_table_args('This is webconsole session table'))
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='session id')
    jti = db.Column(db.String(64), comment='JWT jti')
    expired_at = db.Column(db.DateTime(timezone=True),
                           comment='expired time, for db automatically clear')
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created at')
