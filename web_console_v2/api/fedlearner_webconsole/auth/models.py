
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

from passlib.apps import custom_app_context as pwd_context

from fedlearner_webconsole.db import db, to_dict_mixin


@to_dict_mixin(ignores=['password'])
class User(db.Model):
    __tablename__ = 'users_v2'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), index=True)
    password = db.Column(db.String(255))

    def set_password(self, password):
        self.password = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)
