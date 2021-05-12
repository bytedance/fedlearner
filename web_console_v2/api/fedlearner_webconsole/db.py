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
from contextlib import contextmanager
from enum import Enum
from datetime import datetime, timezone
import os
from typing import Generator, List, Dict, Callable

from flask_sqlalchemy import SQLAlchemy
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

# Explicitly set autocommit and autoflush
# Disables autocommit to make developers to commit manually
# Enables autoflush to make changes visible in the same session
# Enables expire_on_commit to make it possible that one session commit twice
SESSION_OPTIONS = {
    'autocommit': False,
    'autoflush': True,
    'expire_on_commit': True
}
ENGINE_OPTIONS = {}
db = SQLAlchemy(session_options=SESSION_OPTIONS, engine_options=ENGINE_OPTIONS)


def to_dict_mixin(ignores: List[str] = None,
                  extras: Dict[str, Callable] = None):
    if ignores is None:
        ignores = []
    if extras is None:
        extras = {}

    def decorator(cls):
        """A decorator to add a to_dict method to a sqlalchemy model class."""
        def to_dict(self: db.Model):
            """A helper function to convert a sqlalchemy model to dict."""
            dic = {}
            # Puts all columns into the dict
            for col in self.__table__.columns:
                if col.key in ignores:
                    continue
                dic[col.key] = getattr(self, col.key)
            # Puts extra items specified by consumer
            for extra_key, func in extras.items():
                dic[extra_key] = func(self)
            # Converts type
            for key in dic:
                value = dic[key]
                if isinstance(value, datetime):
                    # If there is no timezone, we should treat it as
                    # UTC datetime,otherwise it will be calculated
                    # as local time when converting to timestamp.
                    # Context: all datetime in db is UTC datetime,
                    # see details in db.py#turn_db_timezone_to_utc
                    if value.tzinfo is None:
                        dic[key] = int(
                            value.replace(tzinfo=timezone.utc).timestamp())
                    else:
                        dic[key] = int(value.timestamp())
                elif isinstance(value, Message):
                    dic[key] = MessageToDict(
                        value,
                        preserving_proto_field_name=True,
                        including_default_value_fields=True)
                elif isinstance(value, Enum):
                    dic[key] = value.name
            return dic

        setattr(cls, 'to_dict', to_dict)
        return cls

    return decorator


def default_table_args(comment: str) -> dict:
    return {
        'comment': comment,
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    }


def _turn_db_timezone_to_utc(original_uri: str) -> str:
    """ string operator that make any db into utc timezone

    Args:
        original_uri (str): original uri without set timezone

    Returns:
        str: uri with explicittly set utc timezone
    """
    # Do set use `init_command` for sqlite, since it doesn't support yet
    if original_uri.startswith('sqlite'):
        return original_uri

    _set_timezone_args = 'init_command=SET SESSION time_zone=\'%2B00:00\''
    parsed_uri = original_uri.split('?')

    if len(parsed_uri) == 1:
        return f'{parsed_uri[0]}?{_set_timezone_args}'
    assert len(parsed_uri) == 2, \
        f'failed to parse uri [{original_uri}], since it has more than one ?'

    base_uri, args = parsed_uri
    args = args.split('&&')
    # remove if there's init_command already
    args_list = [_set_timezone_args]
    for a in args:
        if a.startswith('init_command'):
            command = a.split('=')[1]
            # ignore other set time_zone args
            if command.startswith('SET SESSION time_zone'):
                continue
            args_list[0] = f'{args_list[0]};{command}'
        else:
            args_list.append(a)

    args = '&&'.join(args_list)
    return f'{base_uri}?{args}'


def get_database_uri() -> str:
    """Get database uri for whole system.

    - Get database uri:
        - environmental variables
        - default uri that uses sqlite at local file system
    - Process with database uri
        - add a fixed time_zone utc
        - ...


    Returns:
        str: database uri with utc timezone
    """
    uri = ''
    if 'SQLALCHEMY_DATABASE_URI' in os.environ:
        uri = os.getenv('SQLALCHEMY_DATABASE_URI')
    else:
        uri = 'sqlite:///{}'.format(os.path.join(BASE_DIR, 'app.db'))
    return _turn_db_timezone_to_utc(uri)


def get_engine(database_uri: str) -> Engine:
    """get engine according to database uri

    Args:
        database_uri (str): database uri used for create engine

    Returns:
        Engine: engine used for managing connections
    """
    return create_engine(database_uri, **ENGINE_OPTIONS)


@contextmanager
def get_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Get session from database engine.

    Example:
        with get_session(db_engine) as session:
            # write your query, do not need to handle database connection
            session.query(MODEL).filter_by(field=value).first()
    """
    try:
        session = sessionmaker(bind=db_engine, **SESSION_OPTIONS)()
    except Exception:
        raise Exception('unknown db engine')
    else:
        yield session
    finally:
        session.close()


def make_session_context() -> Callable[[], Generator[Session, None, None]]:
    """A functional closure that will store engine
        Call it n times if you want to n connection pools

    Returns:
        Callable[[], Generator[Session, None, None]]:
            a function that yield a context

    Yields:
        Generator[Session, None, None]: a session context

    Examples:
        # First initialize a connection pool,
        # when you want to a new connetion pool
        session_context = make_session_context()
        ...
        # You use it multiple times as follows.
        with session_context() as session:
            session.query(SomeMapperClass).filter_by(id=1).one()
    """
    engine = None

    @contextmanager
    def wrapper_get_session():
        nonlocal engine
        if engine is None:
            engine = get_engine(get_database_uri())
        with get_session(engine) as session:
            yield session

    return wrapper_get_session
