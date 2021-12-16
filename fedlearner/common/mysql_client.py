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
"""MySQL client."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base
from . import fl_logging

Base = declarative_base()


class DatasourceMeta(Base):
    __tablename__ = 'datasource_meta'
    __table_args__ = {'comment': 'data source meta kvstore'}

    id = Column(Integer, primary_key=True, comment='row id')
    kv_key = Column(String(255), nullable=False, unique=True,
                    comment='key for kv store')
    kv_value = Column(Text, comment='value for kv store')


class MySQLClient(object):
    def __init__(self, database, addr, user, password, base_dir):
        self._unix_socket = os.environ.get('DB_SOCKET_PATH', None)
        self._database = database
        self._addr = addr
        self._user = user
        self._password = password
        if self._unix_socket:
            self._addr = ''
            self._password = ''
        self._base_dir = base_dir
        if self._base_dir[0] != '/':
            self._base_dir = '/' + self._base_dir
        self._create_engine_inner()

    def get_data(self, key):
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
            conn_string_pattern = 'mysql+mysqldb://{user}:{passwd}@{addr}'\
                    '/{db_name}'
            conn_string = conn_string_pattern.format(
                user=self._user, passwd=self._password,
                addr=self._addr, db_name=self._database)
            if self._unix_socket:
                sub = '?unix_socket={}'.format(self._unix_socket)
                conn_string = conn_string + sub
            self._engine = create_engine(conn_string, echo=False,
                                        pool_recycle=180)
            # Creates table if not exists
            Base.metadata.create_all(bind=self._engine,
                                     checkfirst=True)
        except Exception as e:
            raise ValueError('create mysql engine failed; [{}]'.\
                format(e))

    @staticmethod
    @contextmanager
    def closing(engine):
        try:
            session = scoped_session(sessionmaker(bind=engine, autoflush=\
                False))()
            yield session
        except Exception as e:
            raise ValueError('Failed to create sql session, error\
                 meesage: {}'.format(e))
        finally:
            session.close()
