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
"""MySQL client for byted."""

from contextlib import contextmanager
from pymysql.constants.CLIENT import FOUND_ROWS
from sqlalchemy.engine import create_engine
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

from bytedmysql import sqlalchemy_init

from . import fl_logging


SESSION_OPTIONS = {'autocommit': False, 'autoflush': True, 'expire_on_commit': False}
MYSQL_OPTIONS = {'connect_args': {'client_flag': FOUND_ROWS}}

Base = declarative_base()


def turn_db_timezone_to_utc(original_uri: str) -> str:
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


class DatasourceMeta(Base):
    __tablename__ = 'datasource_meta'
    __table_args__ = {'comment': 'data source meta kvstore'}

    id = Column(Integer, primary_key=True, comment='row id')
    kv_key = Column(String(255), nullable=False, unique=True,
                    comment='key for kv store')
    kv_value = Column(Text, comment='value for kv store')


class BytedMySQLClient(object):
    def __init__(self, database, addr, user, password, base_dir):
        fl_logging.error(f'lxg log, init, database={database}, addr={addr}, user={user}, password={password}, base_dir={base_dir}')
        self._base_dir = base_dir
        if self._base_dir[0] != '/':
            self._base_dir = '/' + self._base_dir
        sqlalchemy_init()
        self._create_engine_inner()

    def get_data(self, key):
        fl_logging.error(f'lxg log, get_data, key={key}')
        with self.closing(self._engine) as sess:
            try:
                value = sess.query(DatasourceMeta).filter(
                    DatasourceMeta.kv_key == self._generate_key(key)
                ).one().kv_value
                if isinstance(value, str):
                    return value.encode()
                return value
            except NoResultFound:
                return None
            except Exception as e: # pylint: disable=broad-except
                fl_logging.error('failed to get data. msg[%s]', e)
                sess.rollback()
                return None

    def set_data(self, key, data):
        fl_logging.error(f'lxg log, set_data, key={key}, data={data}')
        with self.closing(self._engine) as sess:
            try:
                context = sess.query(DatasourceMeta).filter(
                    DatasourceMeta.kv_key == self._generate_key(key)).first()
                if context:
                    context.kv_value = data
                    sess.commit()
                else:
                    context = DatasourceMeta(
                        kv_key=self._generate_key(key),
                        kv_value=data)
                    sess.add(context)
                    sess.commit()
                return True
            except Exception as e: # pylint: disable=broad-except
                fl_logging.error('failed to set data. msg[%s]', e)
                sess.rollback()
                return False


    def delete(self, key):
        fl_logging.error(f'lxg log, delete, key={key}')
        with self.closing(self._engine) as sess:
            try:
                for context in sess.query(DatasourceMeta).filter(
                    DatasourceMeta.kv_key == self._generate_key(key)):
                    sess.delete(context)
                sess.commit()
                return True
            except Exception as e: # pylint: disable=broad-except
                fl_logging.error('failed to delete. msg[%s]', e)
                sess.rollback()
                return False

    def delete_prefix(self, key):
        fl_logging.error(f'lxg log, delete_prefix, key={key}')
        with self.closing(self._engine) as sess:
            try:
                for context in sess.query(DatasourceMeta).filter(
                    DatasourceMeta.kv_key.like(self._generate_key(key) + '%')):
                    sess.delete(context)
                sess.commit()
                return True
            except Exception as e: # pylint: disable=broad-except
                fl_logging.error('failed to delete prefix. msg[%s]', e)
                sess.rollback()
                return False

    def cas(self, key, old_data, new_data):
        fl_logging.error(f'lxg log, cas, key={key}, old={old_data}, new={new_data}')
        with self.closing(self._engine) as sess:
            try:
                flag = True
                if old_data is None:
                    context = DatasourceMeta(
                        kv_key=self._generate_key(key),
                        kv_value=new_data)
                    sess.add(context)
                    sess.commit()
                else:
                    context = sess.query(DatasourceMeta).filter(
                        DatasourceMeta.kv_key ==\
                        self._generate_key(key)).one()
                    if context.kv_value != old_data:
                        flag = False
                        return flag
                    context.kv_value = new_data
                    sess.commit()
                return flag
            except Exception as e: # pylint: disable=broad-except
                fl_logging.error('failed to cas. msg[%s]', e)
                sess.rollback()
                return False

    def get_prefix_kvs(self, prefix, ignor_prefix=False):
        kvs = []
        path = self._generate_key(prefix)
        fl_logging.error(f'lxg log, get_prefix_kvs, prefix={prefix}, path={path}')
        with self.closing(self._engine) as sess:
            try:
                for context in sess.query(DatasourceMeta).filter(
                    DatasourceMeta.kv_key.like(path + '%')).order_by(
                    DatasourceMeta.kv_key):
                    if ignor_prefix and context.kv_key == path:
                        continue
                    nkey = self._normalize_output_key(context.kv_key,
                        self._base_dir)
                    if isinstance(nkey, str):
                        nkey = nkey.encode()
                    value = context.kv_value
                    if isinstance(value, str):
                        value = value.encode()
                    kvs.append((nkey, value))
                return kvs
            except Exception as e: # pylint: disable=broad-except
                fl_logging.error('failed to get prefix kvs. msg[%s]', e)
                sess.rollback()
                return None

    def _generate_key(self, key):
        nkey = '/'.join([self._base_dir, self._normalize_input_key(key)])
        return nkey

    @staticmethod
    def _normalize_input_key(key):
        skip_cnt = 0
        while key[skip_cnt] == '.' or key[skip_cnt] == '/':
            skip_cnt += 1
        if skip_cnt > 0:
            return key[skip_cnt:]
        return key

    @staticmethod
    def _normalize_output_key(key, base_dir):
        if isinstance(key, str):
            assert key.startswith(base_dir)
        else:
            assert key.decoder().startswith(base_dir)
        return key[len(base_dir)+1:]

    def _create_engine_inner(self):
        try:
            conn_string = self._get_database_uri()
            self._engine = create_engine(conn_string, echo=False,
                                         pool_recycle=180, **MYSQL_OPTIONS)
            # Creates table if not exists
            Base.metadata.create_all(bind=self._engine,
                                     checkfirst=True)
        except Exception as e:
            raise ValueError('create mysql engine failed; [{}]'.\
                format(e))

    def _get_database_uri(self) -> str:
        # uri = environ.get(
        #     'SQLALCHEMY_DATABASE_URI',
        #     'mysql+pymysql://:@/?charset=utf8mb4&binary_prefix=true&&db_psm=toutiao.mysql.aml_fedlearner_write')
        uri = 'mysql+pymysql://:@/?charset=utf8mb4&binary_prefix=true&&db_psm=toutiao.mysql.aml_fedlearner_write'
        return turn_db_timezone_to_utc(uri)

    @staticmethod
    @contextmanager
    def closing(engine):
        try:
            session = scoped_session(sessionmaker(bind=engine, **SESSION_OPTIONS))()
            yield session
        except Exception as e:
            raise ValueError('Failed to create sql session, error\
                 meesage: {}'.format(e))
        finally:
            session.close()
