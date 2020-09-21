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
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.automap import automap_base
from fedlearner.common.mock_mysql import MockMySQLClient
from fedlearner.common.etcd_client import EtcdClient


class DBClient(object):
    def __init__(self, name, addr, user, password, base_dir,
                 use_mock_mysql=False):
        if os.environ.get('USE_ETCD', False):
            self._client = EtcdClient(name, addr, base_dir,
                                      use_mock_mysql)
        else:
            self._client = MySQLClient(name, addr, user,
                                       password, base_dir,
                                       use_mock_mysql)

    def __getattr__(self, attr):
        return getattr(self._client, attr)


class MySQLClient(object):
    def __init__(self, name, addr, user, password, base_dir,
                 use_mock_mysql=False):
        if use_mock_mysql:
            self._client = MockMySQLClient(name, base_dir)
        else:
            self._client = RealMySQLClient(
                name, addr, user, password, base_dir)

    def __getattr__(self, attr):
        return getattr(self._client, attr)

class RealMySQLClient(object):
    def __init__(self, name, addr, user, password, base_dir):
        self._name = name
        self._addr = self._normalize_addr(addr)
        self._user = user
        self._password = password
        self._base_dir = base_dir
        self._create_engine_inner()
        logging.info('success to create table')

    def get_data(self, key):
        with self.closing(self._engine) as sess:
            try:
                table = self._datasource_meta
                value = sess.query(table).filter(table.kv_key ==
                    self._generate_key(key)).one().kv_value
                if isinstance(value, str):
                    return value.encode()
                logging.info('success to get data')
                return value
            except NoResultFound:
                logging.warning('data is not exists')
                return None
            except Exception as e: # pylint: disable=broad-except
                logging.error('failed to get data. msg[%s]', e)
                sess.rollback()
                return None

    def set_data(self, key, data):
        with self.closing(self._engine) as sess:
            try:
                table = self._datasource_meta
                context = sess.query(table).filter(table.kv_key ==
                    self._generate_key(key)).first()
                if context:
                    context.kv_value = data
                    sess.commit()
                else:
                    context = self._datasource_meta(
                        kv_key=self._generate_key(key),
                        kv_value=data)
                    sess.add(context)
                    sess.commit()
                logging.info('success to set data')
                return True
            except Exception as e: # pylint: disable=broad-except
                logging.error('failed to set data. msg[%s]', e)
                sess.rollback()
                return False


    def delete(self, key):
        with self.closing(self._engine) as sess:
            try:
                table = self._datasource_meta
                for context in sess.query(table).filter(table.kv_key ==
                    self._generate_key(key)):
                    sess.delete(context)
                sess.commit()
                logging.info('success to delete')
                return True
            except Exception as e: # pylint: disable=broad-except
                logging.error('failed to delete. msg[%s]', e)
                sess.rollback()
                return False

    def delete_prefix(self, key):
        with self.closing(self._engine) as sess:
            try:
                table = self._datasource_meta
                for context in sess.query(table).filter(table.kv_key.\
                    like(self._generate_key(key) + '%')):
                    sess.delete(context)
                sess.commit()
                logging.info('success to delete prefix')
                return True
            except Exception as e: # pylint: disable=broad-except
                logging.error('failed to delete prefix. msg[%s]', e)
                sess.rollback()
                return False

    def cas(self, key, old_data, new_data):
        with self.closing(self._engine) as sess:
            try:
                table = self._datasource_meta
                flag = True
                if old_data is None:
                    context = self._datasource_meta(
                        kv_key=self._generate_key(key),
                        kv_value=new_data)
                    sess.add(context)
                    sess.commit()
                else:
                    context = sess.query(table).filter(table.kv_key ==\
                        self._generate_key(key)).one()
                    if context.kv_value != old_data:
                        flag = False
                        logging.warning('old data and new data \
                            are not the same')
                        return flag
                    context.kv_value = new_data
                    sess.commit()
                logging.info('success to cas')
                return flag
            except Exception as e: # pylint: disable=broad-except
                logging.error('failed to cas. msg[%s]', e)
                sess.rollback()
                return False

    def get_prefix_kvs(self, prefix, ignor_prefix=False):
        kvs = []
        path = self._generate_key(prefix)
        with self.closing(self._engine) as sess:
            logging.info('start get_prefix_kvs. prefix is [%s] [%s]',
                prefix, path)
            try:
                table = self._datasource_meta
                for context in sess.query(table).filter(table.kv_key.\
                    like(path + '%')).order_by(table.kv_key):
                    logging.info('type of kv_key is[%s]',
                        type(context.kv_key))
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
                logging.info('success to get prefix kvs')
                return kvs
            except Exception as e: # pylint: disable=broad-except
                logging.error('failed to get prefix kvs. msg[%s]', e)
                sess.rollback()
                return None

    def _generate_key(self, key):
        nkey = '/'.join([self._base_dir, self._normalize_input_key(key)])
        return nkey

    @staticmethod
    def _normalize_addr(addr):
        (host, port_str) = addr.split(':')
        try:
            port = int(port_str)
            if port < 0 or port > 65535:
                raise ValueError('port {} is out of range')
        except ValueError:
            raise ValueError('{} is not a valid port'.format(port_str))
        return (host, port_str)

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
        logging.info('normalize ouput key is[%s] type[%s]', key,
            type(key))
        if isinstance(key, str):
            assert key.startswith(base_dir)
        else:
            assert key.decoder().startswith(base_dir)
        return key[len(base_dir)+1:]

    def _create_engine_inner(self):
        try:
            conn_string_pattern = 'mysql://{user}:{passwd}@{host}:'\
                '{port}/{db_name}'
            if os.environ.get('DB_SOCKET_PATH', None):
                host = 'unix://{}'.\
                    format(os.environ.get('DB_SOCKET_PATH'))
                conn_string = conn_string_pattern.format(
                    user=self._user, passwd='',
                    host=host, port=self._addr[1],
                    db_name=self._name)
            else:
                conn_string = conn_string_pattern.format(
                    user=self._user, passwd=self._password,
                    host=self._addr[0], port=self._addr[1],
                    db_name=self._name)
            self._engine = create_engine(conn_string, echo=False,
                                        pool_recycle=180)
            Base = automap_base()
            Base.prepare(self._engine, reflect=True)
            self._datasource_meta = Base.classes.datasource_meta
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
