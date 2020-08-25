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

import threading
import random
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.automap import automap_base
from fedlaerner.common import mock_etcd

class MySQLlient(object):
    MYSQL_CLIENT_POOL_LOCK = threading.Lock()
    MYSQL_CLIENT_POOL = {}
    MYSQL_CLIENT_POOL_DESTORY = False

    def __init__(self, name, addrs, users, passwords, base_dir, use_mock_etcd=False):
        self._name = name
        self._addrs = self._normalize_addr(addrs)
        self._users = self._normalisze_user(users)
        self._passwords = self._normalize_password(passwords)
        self._base_dir = base_dir
        self._check_addrs_users_passwords_legality()
        self._use_mock_etcd = use_mock_etcd
        self._base = automap_base()


    def get_data(self, key):
        addr, password, user = self._get_next_addr_password_user()
        with closing(self.name, addr, password, user, self._use_mock_etcd) as clnt:
            table = self._base.classes.KV
            return clnt.query(table.value).filter(table.key=self._generate_key(key))[0]
    
    def set_data(self, key, data):
        addr, password, user = self._get_next_addr_password_user()
        with closing(self.name, addr, password, user, self._use_mock_etcd) as clnt:
            context = self._base.classes.KV
            context.key = self._generate_key(key)
            context.value = data
            clnt.add(context)
            clnt.commit()

    def delete(self, key):
        addr, password, user = self._get_next_addr_password_user()
        with closing(self.name, addr, password, user, self._use_mock_etcd) as clnt:
            table = self._base.classes.KV
            context = clnt.query(table).filter(table.key=self._generate_key(key))
            clnt.delete(context)
            clnt.commit()

    def delete_prefix(self, key):
        addr, password, user = self._get_next_addr_password_user()
        with closing(self.name, addr, password, user, self._use_mock_etcd) as clnt:
            table = self._base.classes.KV
            contexts = clnt.query(table).filter(table.key.like(self._generate_key(key)+'%'))
            for context in contexts:
                clnt.delete(context)
            clnt.commit()

    def cas(self, key, old_data, new_data):
        addr, password, user = self._get_next_addr_password_user()
        with closing(self.name, addr, password, user, self._use_mock_etcd) as clnt:
            table = self._base.classes.KV
            if old_data is None:
                context = self._base.classes.KV
                context.key = self._generate_key(key)
                context.value = new_data
                clnt.add(context)
                clnt.commit()
            else:
                context = clnt.query(table).filter(table.key=self._generate_key(key))
                flag = True
                if context.value != old_data:
                    flag = False
                context.value = new_data
                clnt.commit()
                return flag

    def get_prefix_kvs(self, prefix, ignor_prefix=False):
        addr, password, user = self._get_next_addr_password_user()
        kvs = []
        path = self._generate_key(preix)
        with closing(self.name, addr, password, user, self._use_mock_etcd) as clnt:
            table = self._base.classes.KV
            contexts = clnt.query(table).filter(table.key.like(path+'%'))
            for context in contexts:
                if ignor_prefix and context.key == path:
                    continue
                nkey = MySQLlient._normalize_output_key(context.key, self._base_dir)
                kvs.append((nkey, context.value))
        return kvs

    def _generate_key(self, key):
        return '/'.join([self._base_dir, self._normalize_input_key(key)])

    def _get_next_addr_password_user(self):
        pos = random.randint(0, len(self._addrs) - 1)
        return self._addrs[pos], self._passwords[pos], self._users[pos]

    @staticmethod
    def _normalize_addr(addrs):
        naddrs = []
        for raw_addr in addrs.split(','):
            (host, port_str) = raw_addr.split(':')
            try:
                port = int(port_str)
                if port < 0 or port > 65535:
                    raise ValueError('port {} is out of range')
            except ValueError:
                raise ValueError('{} is not a valid port'.format(port_str))
            naddrs.append((host, port))
        return naddrs

    @staticmethod
    def _normalize_password(passwords):
        npasswords = []
        for raw_password in passwords.split(','):
            npaaswords.append(raw_password)
        return npasswords

    @staticmethod
    def _normalize_user(users):
        nusers = []
        for raw_user in users.split(','):
            nusers.append(raw_user)
        return nusers

    @staticmethod
    def _normalize_input_key(key):
        skip_cnt = 0
        while key[skip_cnt] == '.' or key[skip_cnt] == '/':
            skip_cnt +=1
        if skip_cnt > 0:
            return key[skip_cnt:]
        return key

    @staticmethod
    def normalize_output_key(key, base_dir):
        if isinstance(base_dir, str):
            assert key.startswith(base_dir.encode())
        else:
            assert key.startswith(base_dir)
        return key[len(base_dir)+1:]

    def _check_addrs_users_passwords_legality(self):
        if len(self.addrs) != len(self.users) or
            len(self.addrs) != len(self.passwords):
            raise ValueError('illegal user list')

    @classmethod
    @contextmanager
    def closing(cls, name, addr, password, user, use_mock_etcd):
        clnt = None
        with cls.MYSQL_CLIENT_POOL_LOCK:
            if (name in cls.MYSQL_CLIENT_POOL and
                len(cls.MYSQL_CLIENT_POOL[name]) > 0):
                if (user in cls.MYSQL_CLIENT_POOL[name] and
                    len(cls.MYSQL_CLIENT_POOL[name][user]) > 0):
                    clnt = cls.MYSQL_CLIENT_POOL[name][user][0]
                    cls.MYSQL_CLIENT_POOL[name] = cls.MYSQL_CLIENT_POOL[name][user][1:]
                    
        if clnt is None:
            try:
                if use_mock_etcd:
                    clnt = mock_etcd.MockEtcdClient(addr[0], addr[1])
                else:
                    conn_string_pattern = 'mysql://{user}:{passwd}@{host}:{port}/{db_name}?charset=utf8&&use_unicode=0'
                    conn_string = conn_string_pattern.format(
                        user=user, password=password, host=addr[0],
                        port=addr[1], db_name=name)
                    engine = create_engine(conn_string, echo=False, poolclass=NullPool)
                    clnt = sessionmaker(bind=engine, autoflush=False)
            except Exception as e:
                clnt.close()
                raise e
        try:
            yield clnt
        except Exception as e:
            clnt.close()
            raise e
        else:
            with cls.MYSQL_CLIENT_POOL_LOCK:
                if cls.MYSQL_CLIENT_POOL_DESTORY:
                    clnt.close()
                else:
                    if name not in cls.MYSQL_CLIENT_POOL:
                        cls.MYSQL_CLIENT_POOL[name][user] = [clnt]
                    else:
                        if user not in cls.MYSQL_CLIENT_POOL[name]:
                            cls.MYSQL_CLIENT_POOL[name][user] = [clnt]
                        else:
                            cls.MYSQL_CLIENT_POOL[name][user].append(clnt)
    
    @classmethod
    def destroy_client_pool(cls):
        with cls.ETCD_CLIENT_POOL_LOCK:
            cls.MYSQL_CLIENT_POOL_DESTORY = True
            for _, user_dict in cls.MYSQL_CLIENT_POOL.items():
                for _, clnts in user_dict.items():
                    for clnt in clnts:
                        clnt.close()

        

    