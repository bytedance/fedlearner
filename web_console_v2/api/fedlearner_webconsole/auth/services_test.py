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

import unittest
from fedlearner_webconsole.auth.models import State, User, Session as SessionTbl
from fedlearner_webconsole.auth.services import UserService, SessionService

from fedlearner_webconsole.db import db
from testing.no_web_server_test_case import NoWebServerTestCase


class UserServiceTest(NoWebServerTestCase):

    def test_get_user_by_id(self):
        # case1: unexisted one
        unexisted_uid = 9999
        with db.session_scope() as session:
            self.assertIsNone(UserService(session).get_user_by_id(unexisted_uid))

        # case2: deleted one
        with db.session_scope() as session:
            deleted_user = User(username='deleted_one', email='who.knows@hhh.com', state=State.DELETED)
            session.add(deleted_user)
            session.commit()
        with db.session_scope() as session:
            self.assertIsNone(UserService(session).get_user_by_id(deleted_user.id, filter_deleted=True))

        # case3: a real one
        with db.session_scope() as session:
            real_user = User(username='real_one', email='who.knows@hhh.com', state=State.ACTIVE)
            session.add(real_user)
            session.commit()
        with db.session_scope() as session:
            self.assertEqual(UserService(session).get_user_by_id(real_user.id).username, 'real_one')

    def test_get_user_by_username(self):
        # case1: unexisted one
        unexisted_username = 'none_existed'
        with db.session_scope() as session:
            self.assertIsNone(UserService(session).get_user_by_username(unexisted_username))

        # case2: deleted one
        with db.session_scope() as session:
            deleted_user = User(username='deleted_one', email='who.knows@hhh.com', state=State.DELETED)
            session.add(deleted_user)
            session.commit()
        with db.session_scope() as session:
            self.assertIsNone(UserService(session).get_user_by_username(deleted_user.username, filter_deleted=True))

        # case3: a real one
        with db.session_scope() as session:
            real_user = User(username='real_one', email='who.knows@hhh.com', state=State.ACTIVE)
            session.add(real_user)
            session.commit()
        with db.session_scope() as session:
            self.assertEqual(UserService(session).get_user_by_username(real_user.username).id, 2)

    def test_get_all_users(self):
        with db.session_scope() as session:
            session.add_all([
                User(username='real_one', email='who.knows@hhh.com', state=State.ACTIVE),
                User(username='deleted_one', email='who.knows@hhh.com', state=State.DELETED)
            ])
            session.commit()
        with db.session_scope() as session:
            self.assertEqual(len(UserService(session).get_all_users()), 2)
            self.assertEqual(len(UserService(session).get_all_users(filter_deleted=True)), 1)

    def test_delete_user(self):
        with db.session_scope() as session:
            user = User(username='real_one', email='who.knows@hhh.com', state=State.ACTIVE)
            session.add(user)
            session.commit()
        with db.session_scope() as session:
            deleted_user = UserService(session).delete_user(user)
            session.commit()
            self.assertEqual(deleted_user.state, State.DELETED)


class SessionServiceTest(NoWebServerTestCase):

    def test_get_session_by_jti(self):
        jti = 'test'
        with db.session_scope() as session:
            session.add(SessionTbl(jti=jti, user_id=1))
            session.commit()
        with db.session_scope() as session:
            session_obj = SessionService(session).get_session_by_jti(jti)
            self.assertEqual(session_obj.jti, jti)
            session_obj = SessionService(session).get_session_by_jti('fjeruif')
            self.assertIsNone(session_obj)

    def test_delete_session(self):
        jti = 'test'
        with db.session_scope() as session:
            session.add(SessionTbl(jti=jti, user_id=1))
            session.commit()
        with db.session_scope() as session:
            session_obj = SessionService(session).get_session_by_jti(jti)
            session_obj = SessionService(session).delete_session(session_obj)
            self.assertEqual(session_obj.jti, jti)
            session.commit()
        with db.session_scope() as session:
            self.assertIsNone(SessionService(session).get_session_by_jti(jti))

        with db.session_scope() as session:
            session_obj = SessionService(session).get_session_by_jti('dfas')
            session_obj = SessionService(session).delete_session(session_obj)
            self.assertIsNone(session_obj)


if __name__ == '__main__':
    unittest.main()
