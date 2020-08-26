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

import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.automap import automap_base
from fedlearner.common.mock_mysql import MockMySQLClient

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

    def get_data(self, key):
        table = self._base.classes.KV
        with self.closing(self._engine) as clnt:
            return clnt.query(table).filter(table.key ==
                self._generate_key(key)).one().value

    def set_data(self, key, data):
        with self.closing(self._engine) as clnt:
            context = self._base.classes.KV()
            context.key = self._generate_key(key)
            context.value = data
            clnt.add(context)
            clnt.commit()

    def delete(self, key):
        with self.closing(self._engine) as clnt:
            table = self._base.classes.KV
            context = clnt.query(table).filter(table.key ==
                self._generate_key(key))
            clnt.delete(context)
            clnt.commit()

    def delete_prefix(self, key):
        with self.closing(self._engine) as clnt:
            table = self._base.classes.KV
            contexts = clnt.query(table).filter(table.key.\
                like(self._generate_key(key).join('%')))
            for context in contexts:
                clnt.delete(context)
            clnt.commit()

    def cas(self, key, old_data, new_data):
        with self.closing(self._engine) as clnt:
            table = self._base.classes.KV
            flag = True
            if old_data is None:
                context = self._base.classes.KV()
                context.key = self._generate_key(key)
                context.value = new_data
                clnt.add(context)
                clnt.commit()
            else:
                context = clnt.query(table).filter(table.key ==\
                    self._generate_key(key))
                if context.value != old_data:
                    flag = False
                context.value = new_data
                clnt.commit()
            return flag

    def get_prefix_kvs(self, prefix, ignor_prefix=False):
        kvs = []
        path = self._generate_key(prefix)
        with self.closing(self._engine) as clnt:
            table = self._base.classes.KV
            contexts = clnt.query(table).filter(table.key.\
                like(path.join('%')))
            for context in contexts:
                if ignor_prefix and context.key == path:
                    continue
                nkey = self._normalize_output_key(context.key, self._base_dir)
                kvs.append((nkey, context.value))
        return kvs

    def _generate_key(self, key):
        return '/'.join([self._base_dir, self._normalize_input_key(key)])

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
        if isinstance(base_dir, str):
            assert key.startswith(base_dir.encode())
        else:
            assert key.startswith(base_dir)
        return key[len(base_dir)+1:]

    def _create_engine_inner(self):
        try:
            conn_string_pattern = 'mysql://{user}:{passwd}@{host}:\
                {port}/{db_name}?charset=utf8&&use_unicode=0'
            conn_string = conn_string_pattern.format(
                user=self._user, password=self._password,
                host=self._addr[0], post=self._addr[1])
            self._engine = create_engine(conn_string, echo=False,
                                        pool_recycle=180)
            self._base = automap_base()
        except Exception as e:
            logging.error('create mysql engine failed; [{}]'.format(e))
            raise e

    @classmethod
    @contextmanager
    def closing(cls, engine):
        try:
            session = scoped_session(sessionmaker(bind=engine, autoflush=\
                False))()
            yield session
        except Exception as e:
            logging.error('Failed to create sql session, error message: {}'.\
                format(e))
            raise e
        finally:
            session.close()
