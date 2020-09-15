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

import threading

class MockMySQL(object):
    def __init__(self, base_dir):
        self._lock = threading.Lock()
        self._data = {}
        self._base_dir = base_dir

    def get_data(self, key):
        with self._lock:
            key = self._generate_key(key)
            if key in self._data:
                if isinstance(self._data[key], str):
                    return self._data[key].encode()
                return self._data[key]
            return None

    def set_data(self, key, value):
        with self._lock:
            key = self._generate_key(key)
            self._data[key] = value

    def delete(self, key):
        with self._lock:
            key = self._generate_key(key)
            self._data.pop(key, None)

    def delete_prefix(self, prefix):
        with self._lock:
            deleted = []
            prefix_key = self._generate_key(prefix)
            for key in self._data:
                if key.startswith(prefix_key):
                    deleted.append(key)
            for key in deleted:
                self._data.pop(key, None)

    def put_if_not_exists(self, key, value):
        with self._lock:
            key = self._generate_key(key)
            if key in self._data:
                return False
            self._data[key] = value
            return True

    def cas(self, key, old_value, new_value):
        with self._lock:
            key = self._generate_key(key)
            stored = None
            if key in self._data:
                stored = self._data[key]
            if stored != old_value:
                return False
            self._data[key] = new_value
            return True

    def get_prefix_kvs(self, prefix, ignor_prefix=False):
        kvs = []
        path = self._generate_key(prefix)
        for key, value in self._data.items():
            if key.startswith(path):
                if ignor_prefix and path == key:
                    continue
                nkey = self._normalize_output_key(key, self._base_dir)
                if isinstance(value, str):
                    value = value.encode()
                kvs.append((nkey, value))
        kvs = sorted(kvs, key=lambda kv: kv[0], reverse=False)
        return kvs

    def _generate_key(self, key):
        nkey = '/'.join([self._base_dir, self._normalize_input_key(key)])
        if isinstance(nkey, str):
            nkey = nkey.encode()
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
        if isinstance(base_dir, str):
            assert key.startswith(base_dir.encode())
        else:
            assert key.startswith(base_dir)
        return key[len(base_dir)+1:]

    def destroy_client_pool(self):
        with self._lock:
            self._data.clear()


class MockMySQLClient(object):
    MOCK_MYSQL_CLIENT_POOL = {}
    MOCK_MYSQL_CLIENT_POOL_LOCK = threading.Lock()

    def __init__(self, name, base_dir):
        with self.MOCK_MYSQL_CLIENT_POOL_LOCK:
            if base_dir not in self.MOCK_MYSQL_CLIENT_POOL:
                self.MOCK_MYSQL_CLIENT_POOL[base_dir] = MockMySQL(base_dir)
            self._mock_mysql = self.MOCK_MYSQL_CLIENT_POOL[base_dir]

    def __getattr__(self, attr):
        return getattr(self._mock_mysql, attr)
