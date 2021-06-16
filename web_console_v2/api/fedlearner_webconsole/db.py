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

# coding: utf-8
import os
from contextlib import contextmanager
from typing import ContextManager, Callable

import sqlalchemy as sa

from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.declarative.api import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from flask_sqlalchemy import SQLAlchemy

from envs import Envs
BASE_DIR = Envs.BASE_DIR

# Explicitly set autocommit and autoflush
# Disables autocommit to make developers to commit manually
# Enables autoflush to make changes visible in the same session
# Disable expire_on_commit to make it possible that object can detach
SESSION_OPTIONS = {
    'autocommit': False,
    'autoflush': True,
    'expire_on_commit': False
}
ENGINE_OPTIONS = {}


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
        uri = 'sqlite:///{}?check_same_thread=False'.format(
            os.path.join(BASE_DIR, 'app.db'))
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
def get_session(db_engine: Engine) -> ContextManager[Session]:
    """Get session from database engine.

    Example:
        with get_session(db_engine) as session:
            # write your query, do not need to handle database connection
            session.query(MODEL).filter_by(field=value).first()
    """
    try:
        session: Session = sessionmaker(bind=db_engine, **SESSION_OPTIONS)()
    except Exception:
        raise Exception('unknown db engine')

    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def make_session_context() -> Callable[[], ContextManager[Session]]:
    """A functional closure that will store engine
        Call it n times if you want to n connection pools

    Returns:
        Callable[[], Callable[[], ContextManager[Session]]]
            a function that return a contextmanager


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

    def wrapper_get_session():
        nonlocal engine
        if engine is None:
            engine = get_engine(get_database_uri())
        return get_session(engine)

    return wrapper_get_session


class DBHandler(object):
    def __init__(self) -> None:
        super().__init__()

        self.engine: Engine = get_engine(get_database_uri())
        self.Model: DeclarativeMeta = declarative_base(bind=self.engine)
        for module in sa, sa.orm:
            for key in module.__all__:
                if not hasattr(self, key):
                    setattr(self, key, getattr(module, key))

    def session_scope(self) -> ContextManager[Session]:
        return get_session(self.engine)

    @property
    def metadata(self) -> DeclarativeMeta:
        return self.Model.metadata

    def rebind(self, database_uri: str):
        self.engine = get_engine(database_uri)
        self.Model = declarative_base(bind=self.engine, metadata=self.metadata)

    def create_all(self):
        return self.metadata.create_all()

    def drop_all(self):
        return self.metadata.drop_all()


# now db_handler and db are alive at the same time
# db will be replaced by db_handler in the near future
db_handler = DBHandler()
db = SQLAlchemy(session_options=SESSION_OPTIONS,
                engine_options=ENGINE_OPTIONS,
                metadata=db_handler.metadata)
