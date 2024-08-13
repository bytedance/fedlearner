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
import json
import logging
import uuid
from abc import ABCMeta, abstractmethod
from datetime import timedelta, timezone
from typing import Optional
from collections import namedtuple
from http import HTTPStatus
from functools import wraps
from urllib.parse import urlencode

import requests
import jwt
from flask import request, g
import xmltodict
from google.protobuf.json_format import ParseDict
from config import Config
from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.const import SSO_HEADER
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.utils.decorators.lru_cache import lru_cache
from fedlearner_webconsole.utils.pp_datetime import now, to_timestamp
from fedlearner_webconsole.utils.flask_utils import set_current_user
from fedlearner_webconsole.utils.pp_base64 import base64decode
from fedlearner_webconsole.proto.auth_pb2 import SigninParameter, Sso
from fedlearner_webconsole.exceptions import UnauthorizedException, InvalidArgumentException, NoAccessException
from fedlearner_webconsole.auth.services import UserService, SessionService, StrictSignInService
from fedlearner_webconsole.auth.models import Session, State, User

UserInfo = namedtuple('UserInfo', ['username', 'email'])


class SsoProtocol(enum.Enum):
    OAUTH = 'oauth'
    CAS = 'cas'


def _generate_jwt_session(username: str, user_id: int, session: Session) -> str:
    delta = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
    expire_time = now(timezone.utc) + delta
    jti = str(uuid.uuid4())
    token = jwt.encode(
        {
            'username': username,
            'exp': expire_time,
            'jti': jti
        },
        key=Config.JWT_SECRET_KEY,
    )
    session_obj = Session(jti=jti, user_id=user_id, expired_at=expire_time)
    session.add(session_obj)
    # PyJWT api has a breaking change for return types
    if isinstance(token, bytes):
        token = token.decode()
    return token


def _signout_jwt_session():
    if hasattr(g, 'jti'):
        jti = g.jti
    else:
        raise UnauthorizedException('Not sign in with jwt.')
    with db.session_scope() as session:
        session_obj = SessionService(session).get_session_by_jti(jti)
        SessionService(session).delete_session(session_obj)
        session.commit()


def _validate_jwt_session(credentials: str) -> str:
    time_now = to_timestamp(now(timezone.utc))
    decoded_token = jwt.decode(credentials, Config.JWT_SECRET_KEY, algorithms='HS256')
    expire_time = decoded_token.get('exp')
    jti = decoded_token.get('jti')
    username = decoded_token.get('username')
    with db.session_scope() as session:
        session = SessionService(session).get_session_by_jti(jti)
    if session is None:
        raise UnauthorizedException('No session.')
    if expire_time < time_now:
        raise UnauthorizedException('Token has expired.')
    # Set jti to for signout to find the session to remove.
    g.jti = jti
    return username


class SsoHandler(metaclass=ABCMeta):

    def __init__(self, sso):
        self.sso = sso

    @abstractmethod
    def signin(self, signin_parameter: SigninParameter) -> dict:
        pass

    @abstractmethod
    def signout(self):
        pass

    @abstractmethod
    def check_credentials(self, credentials) -> str:
        """
        Check credentials and return the username.
        """

    def check_credentials_and_set_current_user(self, credentials):
        try:
            username = self.check_credentials(credentials)
        except Exception as err:
            raise UnauthorizedException(str(err)) from err
        with db.session_scope() as session:
            user = UserService(session).get_user_by_username(username, filter_deleted=True)
            if user is None:
                raise UnauthorizedException(f'User {username} not found.')
        set_current_user(user)

    @classmethod
    def check_user_validity(cls, user: User):
        if user.state == State.DELETED:
            error_msg = f'user: {user.username} has been deleted'
            logging.error(error_msg)
            raise InvalidArgumentException(error_msg)


class OAuthHandler(SsoHandler):

    def get_access_token(self, code: str) -> str:
        try:
            r = requests.post(self.sso.oauth.access_token_url,
                              data={
                                  'code': code,
                                  'client_id': self.sso.oauth.client_id,
                                  'client_secret': self.sso.oauth.secret,
                                  'redirect_uri': self.sso.oauth.redirect_uri,
                                  'grant_type': 'authorization_code'
                              })
        except Exception as e:
            error_msg = f'Get access_token failed from sso: {self.sso.name}: {str(e)}.'
            logging.error(error_msg)
            raise UnauthorizedException(error_msg) from e
        if r.status_code != HTTPStatus.OK:
            error_msg = f'Get access_token failed from sso: {self.sso.name}: {r.json()}.'
            logging.error(error_msg)
            raise UnauthorizedException(error_msg)
        access_token = r.json().get('access_token')
        if access_token is None:
            error_msg = f'Get access_token failed from sso: ' \
                        f'{self.sso.name}: no access_token in response.'
            logging.error(error_msg)
            raise UnauthorizedException(error_msg)
        return access_token

    def get_user_info(self, access_token: str) -> UserInfo:
        user_info = get_user_info_with_cache(self.sso.name, self.sso.oauth.user_info_url, access_token,
                                             self.sso.oauth.username_key, self.sso.oauth.email_key)
        return user_info

    def signin(self, signin_parameter: SigninParameter) -> dict:
        code = signin_parameter.code
        if code == '':
            raise InvalidArgumentException('OAuth code is not found')
        access_token = self.get_access_token(code)

        user_info = self.get_user_info(access_token)

        with db.session_scope() as session:
            user = UserService(session).create_user_if_not_exists(username=user_info.username,
                                                                  email=user_info.email,
                                                                  sso_name=self.sso.name,
                                                                  name=user_info.username)
            self.check_user_validity(user)
            StrictSignInService(session).update(user, is_signed_in=True)
            session.commit()
            return {'user': user.to_dict(), 'access_token': access_token}

    def signout(self):
        get_user_info_with_cache.cache_clear()

    def check_credentials(self, credentials):
        user_info = get_user_info_with_cache(self.sso.name, self.sso.oauth.user_info_url, credentials,
                                             self.sso.oauth.username_key, self.sso.oauth.email_key)
        return user_info.username


class JwtHandler(SsoHandler):

    def __init__(self):
        super().__init__(None)

    def signin(self, signin_parameter: SigninParameter) -> dict:
        username = signin_parameter.username
        password = base64decode(signin_parameter.password)
        if username == '' or password == '':
            raise InvalidArgumentException('username or password is not found')
        with db.session_scope() as session:
            user = UserService(session).get_user_by_username(username, filter_deleted=True)
            if user is None:
                raise InvalidArgumentException(f'Failed to find user: {username}')
            strict_service = StrictSignInService(session)
            if not strict_service.can_sign_in(user):
                raise NoAccessException('Account is locked')
            if not user.verify_password(password):
                logging.warning(f'user {user.username} login failed due to wrong password')
                emit_store('user.wrong_password', 1)
                strict_service.update(user, is_signed_in=False)
                session.commit()
                raise InvalidArgumentException('Invalid password')
            token = _generate_jwt_session(username, user.id, session)
            strict_service.update(user, is_signed_in=True)
            session.commit()
        return {'user': user.to_dict(), 'access_token': token}

    def signout(self):
        _signout_jwt_session()

    def check_credentials(self, credentials: str) -> str:
        return _validate_jwt_session(credentials)


class CasHandler(SsoHandler):

    def _service_validate(self, ticket: str) -> str:
        params_dict = dict(
            service=self.sso.cas.service_url,
            ticket=ticket,
        )
        validate_url = f'{self.sso.cas.cas_server_url}' \
                       f'{self.sso.cas.validate_route}?{urlencode(params_dict)}'
        r = requests.get(validate_url)
        if r.status_code != HTTPStatus.OK:
            logging.error(f'Cas sso {self.sso.name} receive Error code {r.status_code}')
            raise UnauthorizedException('Sso server error.')
        resp_dict = xmltodict.parse(r.content)
        if 'cas:authenticationSuccess' in resp_dict['cas:serviceResponse']:
            resp_data = resp_dict['cas:serviceResponse']['cas:authenticationSuccess']
            return resp_data['cas:user']
        logging.error(f'sso: {self.sso.name} CAS returned unexpected result')
        raise UnauthorizedException('Wrong ticket.')

    def signin(self, signin_parameter: SigninParameter) -> dict:
        ticket = signin_parameter.ticket
        if ticket == '':
            raise InvalidArgumentException('CAS ticket is not found')
        username = self._service_validate(ticket)

        with db.session_scope() as session:
            user = UserService(session).create_user_if_not_exists(username=username,
                                                                  name=username,
                                                                  email='',
                                                                  sso_name=self.sso.name)
            self.check_user_validity(user)
            session.flush()
            token = _generate_jwt_session(username, user.id, session)
            StrictSignInService(session).update(user, is_signed_in=True)
            session.commit()
            return {'user': user.to_dict(), 'access_token': token}

    def signout(self):
        _signout_jwt_session()

    def check_credentials(self, credentials: str) -> str:
        return _validate_jwt_session(credentials)


class SsoInfos:

    def __init__(self):
        try:
            sso_infos_dict = json.loads(Envs.SSO_INFOS)
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f'Failed parse SSO_INFOS: {str(e)}')
            sso_infos_dict = []
        self.sso_infos = []
        # sso_infos without server info which should not be visible to the frontend
        self.sso_handlers = {}
        for sso in sso_infos_dict:
            # check the format of sso_infos
            sso_proto = ParseDict(sso, Sso(), ignore_unknown_fields=True)
            if sso_proto.name == 'default':
                logging.error('Sso name should not be \'default\'')
            self.sso_infos.append(sso_proto)
            if sso_proto.WhichOneof('protocol') == SsoProtocol.OAUTH.value:
                self.sso_handlers[sso_proto.name] = OAuthHandler(sso_proto)
            elif sso_proto.WhichOneof('protocol') == SsoProtocol.CAS.value:
                self.sso_handlers[sso_proto.name] = CasHandler(sso_proto)
            else:
                logging.error(f'SSO {sso_proto.name} does not have supported protocol.')
        self.sso_handlers['default'] = JwtHandler()

    def get_sso_info(self, name: str) -> Optional[Sso]:
        for sso in self.sso_infos:
            if name == sso.name:
                return sso
        return None


sso_info_manager = SsoInfos()


class SsoHandlerFactory:

    @staticmethod
    def get_handler(sso_name) -> SsoHandler:
        jwt_handler = sso_info_manager.sso_handlers['default']
        return sso_info_manager.sso_handlers.get(sso_name, jwt_handler)


# Separate the func from the class to avoid leaking memory.
@lru_cache(timeout=600, maxsize=128)
def get_user_info_with_cache(sso_name: str, user_info_url: str, access_token: str, username_key: str,
                             email_key: str) -> Optional[UserInfo]:
    if not username_key:
        username_key = 'username'
    if not email_key:
        email_key = 'email'
    try:
        r = requests.get(user_info_url, headers={'Authorization': f'Bearer {access_token}'})
    except Exception as e:  # pylint: disable=broad-except
        error_msg = f'Get user_info failed from sso: {sso_name}: {str(e)}.'
        logging.error(error_msg)
        raise UnauthorizedException(error_msg) from e
    if r.status_code != HTTPStatus.OK:
        error_msg = f'Get user_info failed from sso: {sso_name}: {r.json()}.'
        logging.error(error_msg)
        raise UnauthorizedException(error_msg)
    user_info_dict = r.json()
    # This is to be compatible with some API response schema with data.
    if 'data' in user_info_dict:
        user_info_dict = user_info_dict.get('data')
    if username_key not in user_info_dict:
        error_msg = f'Get user_info failed from sso: ' \
                    f'{sso_name}: no {username_key} in response.'
        logging.error(error_msg)
        raise UnauthorizedException(error_msg)
    user_info = UserInfo(username=user_info_dict.get(username_key), email=user_info_dict.get(email_key, ''))
    return user_info


def credentials_required(fn):

    @wraps(fn)
    def decorator(*args, **kwargs):

        sso_headers = request.headers.get(SSO_HEADER, None)
        jwt_headers = request.headers.get('Authorization', None)
        sso_name = None

        if sso_headers is None and jwt_headers is None and Envs.DEBUG:
            return fn(*args, **kwargs)

        if sso_headers:
            sso_name, _, credentials = sso_headers.split()
        elif jwt_headers:
            _, credentials = jwt_headers.split()
        else:
            raise UnauthorizedException(f'failed to find {SSO_HEADER} or authorization within headers')
        SsoHandlerFactory.get_handler(sso_name).check_credentials_and_set_current_user(credentials)
        return fn(*args, **kwargs)

    return decorator
