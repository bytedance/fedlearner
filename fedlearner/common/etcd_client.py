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
"""Etcd client."""

import socket
import threading
import random
from contextlib import contextmanager

import etcd3

class EtcdClient(object):
    ETCD_CLIENT_POOL_LOCK = threading.Lock()
    ETCD_CLIENT_POOL = {}
    ETCD_CLIENT_POOL_DESTORY = False

    def __init__(self, name, addrs, base_dir):
        if len(base_dir) == 0 or base_dir[0] != '/':
            base_dir = '/' + base_dir
        self._name = name
        self._base_dir = base_dir
        self._addrs = self._normalize_addr(addrs)
        if len(self._addrs) == 0:
            raise ValueError('Empty hosts EtcdClient')
        self._cur_addr_idx = random.randint(0, len(self._addrs) - 1)

    def get_data(self, key):
        addr = self._get_next_addr()
        with EtcdClient.closing(self._name, addr) as clnt:
            return clnt.get(self._generate_path(key))[0]

    def set_data(self, key, data):
        addr = self._get_next_addr()
        with EtcdClient.closing(self._name, addr) as clnt:
            clnt.put(self._generate_path(key), data)

    def delete(self, key):
        addr = self._get_next_addr()
        with EtcdClient.closing(self._name, addr) as clnt:
            return clnt.delete(self._generate_path(key))

    def delete_prefix(self, key):
        addr = self._get_next_addr()
        with EtcdClient.closing(self._name, addr) as clnt:
            return clnt.delete_prefix(self._generate_path(key))

    def cas(self, key, old_data, new_data):
        addr = self._get_next_addr()
        with EtcdClient.closing(self._name, addr) as clnt:
            etcd_path = self._generate_path(key)
            if old_data is None:
                return clnt.put_if_not_exists(etcd_path, new_data)
            return clnt.replace(etcd_path, old_data, new_data)

    def watch_key(self, key):
        addr = self._get_next_addr()
        with EtcdClient.closing(self._name, addr) as clnt:
            return clnt.watch(self._generate_path(key))

    def get_prefix_kvs(self, prefix):
        addr = self._get_next_addr()
        kvs = []
        with EtcdClient.closing(self._name, addr) as clnt:
            for (data, key) in clnt.get_prefix(prefix, sort_order='ascend'):
                kvs.append((key.key, data))
        return kvs

    def _generate_path(self, key):
        return '/'.join([self._base_dir, key])

    def _get_next_addr(self):
        return self._addrs[random.randint(0, len(self._addrs) - 1)]

    @staticmethod
    def _normalize_addr(addrs):
        naddrs = []
        for raw_addr in addrs.split(','):
            (ip, port_str) = raw_addr.split(':')
            if ip != 'localhost':
                try:
                    socket.inet_aton(ip)
                    if ip.count('.') != 3:
                        raise socket.error
                except socket.error:
                    raise ValueError('{} is not a valid ip'.format(ip))
            try:
                port = int(port_str)
                if port < 0 or port > 65535:
                    raise ValueError('port {} is out of range')
            except ValueError:
                raise ValueError('{} is not a valid port'.format(port_str))
            naddrs.append((ip, port))
        return naddrs

    @classmethod
    @contextmanager
    def closing(cls, name, addr):
        clnt = None
        with cls.ETCD_CLIENT_POOL_LOCK:
            if (name in cls.ETCD_CLIENT_POOL and
                    len(cls.ETCD_CLIENT_POOL[name]) > 0):
                clnt = cls.ETCD_CLIENT_POOL[name][0]
                cls.ETCD_CLIENT_POOL[name] = cls.ETCD_CLIENT_POOL[name][1:]
        if clnt is None:
            try:
                clnt = etcd3.client(host=addr[0], port=addr[1])
            except Exception as e:
                clnt.close()
                raise e
        try:
            yield clnt
        except Exception as e:
            clnt.close()
            raise e
        else:
            with cls.ETCD_CLIENT_POOL_LOCK:
                if cls.ETCD_CLIENT_POOL_DESTORY:
                    clnt.close()
                else:
                    if name not in cls.ETCD_CLIENT_POOL:
                        cls.ETCD_CLIENT_POOL[name] = [clnt]
                    else:
                        cls.ETCD_CLIENT_POOL[name].append(clnt)

    @classmethod
    def destory_client_pool(cls):
        with cls.ETCD_CLIENT_POOL_LOCK:
            cls.ETCD_CLIENT_POOL_DESTORY = True
            for _, clnts in cls.ETCD_CLIENT_POOL.items():
                for clnt in clnts:
                    clnt.close()
