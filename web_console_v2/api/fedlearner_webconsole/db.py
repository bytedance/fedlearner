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
import os
from contextlib import contextmanager
from typing import ContextManager
from pymysql.constants.CLIENT import FOUND_ROWS
import sqlalchemy as sa
from sqlalchemy import orm, event, null
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeMeta, declarative_base
from sqlalchemy.orm.session import Session

from envs import Envs
from fedlearner_webconsole.utils.base_model.softdelete_model import SoftDeleteModel

BASE_DIR = Envs.BASE_DIR

# Explicitly set autocommit and autoflush
# Disables autocommit to make developers to commit manually
# Enables autoflush to make changes visible in the same session
# Disable expire_on_commit to make it possible that object can detach
SESSION_OPTIONS = {'autocommit': False, 'autoflush': True, 'expire_on_commit': False}
# Add flag FOUND_ROWS to make update statement return matched rows but not changed rows.
# When use Sqlalchemy, must set this flag to make update statement validation bug free.
MYSQL_OPTIONS = {'connect_args': {'client_flag': FOUND_ROWS}}
SQLITE_OPTIONS = {}


def default_table_args(comment: str) -> dict:
    return {
        'comment': comment,
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    }


# an option is added to all SELECT statements that will limit all queries against Dataset to filter on deleted == null
# global WHERE/ON criteria eg: https://docs.sqlalchemy.org/en/14/_modules/examples/extending_query/filter_public.html
# normal orm execution wont get the soft-deleted data, eg: session.query(A).get(1)
# use options can get the soft-deleted data eg: session.query(A).execution_options(include_deleted=True).get(1)
@event.listens_for(Session, 'do_orm_execute')
def _add_filtering_criteria(execute_state):
    if (not execute_state.is_column_load and not execute_state.execution_options.get('include_deleted', False)):
        execute_state.statement = execute_state.statement.options(
            orm.with_loader_criteria(
                SoftDeleteModel,
                lambda cls: cls.deleted_at == null(),
                include_aliases=True,
            ))


def turn_db_timezone_to_utc(original_uri: str) -> str:
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
    uri = Envs.SQLALCHEMY_DATABASE_URI
    if not uri:
        db_path = os.path.join(BASE_DIR, 'app.db')
        uri = f'sqlite:///{db_path}?check_same_thread=False'
    return turn_db_timezone_to_utc(uri)


def _get_engine(database_uri: str) -> Engine:
    """Gets engine according to database uri.

    Args:
        database_uri (str): database uri used for create engine

    Returns:
        Engine: engine used for managing connections
    """
    engine_options = {}
    if database_uri.startswith('mysql'):
        engine_options = MYSQL_OPTIONS
    elif database_uri.startswith('sqlite'):
        engine_options = SQLITE_OPTIONS
    return create_engine(database_uri, **engine_options)


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
    except Exception as e:
        raise Exception('unknown db engine') from e

    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DBHandler(object):

    def __init__(self) -> None:
        super().__init__()

        self.engine: Engine = _get_engine(get_database_uri())
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
        self.engine = _get_engine(database_uri)
        self.Model = declarative_base(bind=self.engine, metadata=self.metadata)

    def create_all(self):
        return self.metadata.create_all()

    def drop_all(self):
        return self.metadata.drop_all()


# now db and db are alive at the same time
# db will be replaced by db in the near future
db = DBHandler()
