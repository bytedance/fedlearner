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
from typing import List, Optional
from sqlalchemy.orm import Session

from fedlearner_webconsole.auth.models import State, User, Session as SessionTbl, Role
from fedlearner_webconsole.iam.client import create_iams_for_user
from fedlearner_webconsole.utils.const import SIGN_IN_INTERVAL_SECONDS, MAX_SIGN_IN_ATTEMPTS
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp


class UserService(object):

    def __init__(self, session: Session):
        self._session = session

    def _filter_deleted_user(self, user: User) -> Optional[User]:
        if not user or user.state == State.DELETED:
            return None
        return user

    def get_user_by_id(self, user_id: int, filter_deleted=False) -> Optional[User]:
        user = self._session.query(User).filter_by(id=user_id).first()
        if filter_deleted:
            return self._filter_deleted_user(user)
        return user

    def get_user_by_username(self, username: str, filter_deleted=False) -> Optional[User]:
        user = self._session.query(User).filter_by(username=username).first()
        if filter_deleted:
            return self._filter_deleted_user(user)
        return user

    def get_all_users(self, filter_deleted=False) -> List[User]:
        if filter_deleted:
            return self._session.query(User).filter_by(state=State.ACTIVE).all()
        return self._session.query(User).all()

    def delete_user(self, user: User) -> User:
        user.state = State.DELETED
        return user

    def create_user_if_not_exists(self,
                                  username: str,
                                  email: str,
                                  name: Optional[str] = None,
                                  role: Role = Role.USER,
                                  sso_name: Optional[str] = None,
                                  password: Optional[str] = None) -> User:
        user = self.get_user_by_username(username)
        if user is None:
            user = User(username=username, name=name, email=email, state=State.ACTIVE, role=role, sso_name=sso_name)
            if password is not None:
                user.set_password(password)
            self._session.add(user)
            create_iams_for_user(user)
        return user


class SessionService(object):

    def __init__(self, session: Session):
        self._session = session

    def get_session_by_jti(self, jti: str) -> Optional[SessionTbl]:
        return self._session.query(SessionTbl).filter_by(jti=jti).first()

    def delete_session(self, session_obj: SessionTbl) -> Optional[SessionTbl]:
        if session_obj is None:
            logging.warning('deleting a non-existence session...')
            return None
        self._session.delete(session_obj)
        return session_obj

    def delete_session_by_user_id(self, user_id: int) -> Optional[SessionTbl]:
        session_obj = self._session.query(SessionTbl).filter(SessionTbl.user_id == user_id).first()
        return self.delete_session(session_obj)


class StrictSignInService(object):

    def __init__(self, session: Session):
        self._session = session

    def can_sign_in(self, user: User):
        if user.last_sign_in_at is None or \
           to_timestamp(now()) - to_timestamp(user.last_sign_in_at) > SIGN_IN_INTERVAL_SECONDS:
            return True
        return not user.failed_sign_in_attempts >= MAX_SIGN_IN_ATTEMPTS

    def update(self, user: User, is_signed_in: bool = True):
        user.last_sign_in_at = now()
        if is_signed_in:
            user.failed_sign_in_attempts = 0
        else:
            user.failed_sign_in_attempts += 1
