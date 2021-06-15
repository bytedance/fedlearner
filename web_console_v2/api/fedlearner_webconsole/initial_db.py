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

from fedlearner_webconsole.auth.models import User, Role, State
from fedlearner_webconsole.db import db_handler as db

INITIAL_USER_INFO = [{
    'username': 'ada',
    'password': 'fl@123.',
    'name': 'ada',
    'email': 'ada@fedlearner.com',
    'role': Role.USER,
    'state': State.ACTIVE,
}, {
    'username': 'admin',
    'password': 'fl@123.',
    'name': 'admin',
    'email': 'admin@fedlearner.com',
    'role': Role.ADMIN,
    'state': State.ACTIVE,
}]


def initial_db():
    with db.session_scope() as session:
        # initial user info first
        for u_info in INITIAL_USER_INFO:
            username = u_info['username']
            password = u_info['password']
            name = u_info['name']
            email = u_info['email']
            role = u_info['role']
            state = u_info['state']
            if session.query(User).filter_by(
                    username=username).first() is None:
                user = User(username=username,
                            name=name,
                            email=email,
                            role=role,
                            state=state)
                user.set_password(password=password)
                session.add(user)
        session.commit()
