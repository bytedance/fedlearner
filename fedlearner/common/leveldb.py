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
"""LevelDB"""

import leveldb

def encode(k):
    if isinstance(k, int):
        k = str(k)
    if isinstance(k, str):
        k = k.encode()
    return k

class LevelDB(object):
    """Thread-safe"""
    def __init__(self, dbpath):
        self._db = leveldb.LevelDB(dbpath) #pylint: disable=c-extension-no-member

    def get_data(self, key):
        return bytes(self._db.Get(encode(key)))

    def set_data(self, key, data):
        return self._db.Put(encode(key), data)

    def delete(self, key):
        return self._db.Delete(encode(key))

    def delete_prefix(self, key):
        raise NotImplementedError

    def cas(self, key, old_data, new_data):
        raise NotImplementedError

    def get_prefix_kvs(self, prefix, ignore_prefix=False):
        raise NotImplementedError
