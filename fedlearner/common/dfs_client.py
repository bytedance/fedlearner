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
"""DFS client."""

import os

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile
from tensorflow.python.lib.io import file_io #pylint: disable=no-name-in-module

from . import fl_logging


class DFSClient(object):
    """
    support HDFS and NFS
    """

    def __init__(self, base_dir):
        self._meta_filename = "meta"
        self._base_dir = base_dir

    def get_data(self, key):
        key_path = self._generate_path(key)
        if not gfile.Exists(key_path):
            return None
        with gfile.Open(self._generate_path(key), 'rb') as file:
            return file.read()

    def set_data(self, key, data):
        key_path = self._generate_path(key)
        base_dir = os.path.dirname(key_path)
        if not gfile.Exists(base_dir):
            try:
                gfile.MakeDirs(base_dir)
            except tf.errors.OpError as e:  # pylint: disable=broad-except
                fl_logging.warning("create directory %s failed,"
                                " reason: %s", base_dir, str(e))
                return False
        file_io.atomic_write_string_to_file(key_path, data)
        return True

    def delete(self, key):
        try:
            gfile.Remove(self._generate_path(key))
            return True
        except tf.errors.OpError as e:
            fl_logging.warning("delete key %s failed, reason: %s",
                            key, str(e))
            return False

    def delete_prefix(self, key):
        try:
            gfile.DeleteRecursively(self._generate_path(key, with_meta=False))
            return True
        except Exception as e:   # pylint: disable=broad-except
            fl_logging.warning("delete prefix with key %s failed,"
                            " reason: %s", key, str(e))
            return False

    def cas(self, key, old_data, new_data):
        org_data = self.get_data(key)
        if isinstance(org_data, bytes):
            org_data = org_data.decode('utf-8')
        if isinstance(old_data, bytes):
            old_data = old_data.decode('utf-8')
        if org_data != old_data:
            fl_logging.warning("CAS failed. \norg data: %s old data: %s"
                            " new data: %s", org_data, old_data, new_data)
            return False
        return self.set_data(key, new_data)

    def get_prefix_kvs(self, prefix, ignore_prefix=False):
        kvs = []
        target_path = self._generate_path(prefix, with_meta=False)
        cur_paths = [target_path]
        children_paths = []
        while cur_paths:
            for path in cur_paths:
                filenames = []
                try:
                    if gfile.IsDirectory(path):
                        filenames = gfile.ListDirectory(path)
                except Exception as e:  # pylint: disable=broad-except
                    fl_logging.warning("get prefix kvs %s failed, "
                                    " reason: %s", path, str(e))
                    break
                for filename in sorted(filenames):
                    file_path = "/".join([path, filename])
                    if gfile.IsDirectory(file_path):
                        children_paths.append(file_path)
                    else:
                        if ignore_prefix and path == target_path:
                            continue
                        nkey = self.normalize_output_key(
                            path, self._base_dir).encode()
                        with gfile.Open(file_path, 'rb') as file:
                            kvs.append((nkey, file.read()))
            cur_paths = children_paths
            children_paths = []
        return kvs

    def _generate_path(self, key, with_meta=True):
        if with_meta:
            return '/'.join([self._base_dir, self._normalize_input_key(key),
                             self._meta_filename])
        return '/'.join([self._base_dir, self._normalize_input_key(key)])

    @staticmethod
    def _normalize_input_key(key):
        skip_cnt = 0
        while key[skip_cnt] == '.' or key[skip_cnt] == '/':
            skip_cnt += 1
        if skip_cnt > 0:
            return key[skip_cnt:]
        return key

    @staticmethod
    def normalize_output_key(key, base_dir):
        if isinstance(base_dir, str):
            assert key.startswith(base_dir)
        else:
            assert key.startswith(base_dir)
        return key[len(base_dir)+1:]

    @classmethod
    def destroy_client_pool(cls):
        pass
