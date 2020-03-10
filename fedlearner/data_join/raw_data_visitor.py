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

import logging
import os

import tensorflow as tf
from google.protobuf import text_format
from tensorflow.python.platform import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import visitor
from fedlearner.data_join.raw_data_iter_impl import create_raw_data_iter
from fedlearner.data_join.common import (
    RawDataIndexSuffix, RawDataUnIndexSuffix
)

class RawDataManager(visitor.IndexMetaManager):
    def __init__(self, etcd, data_source, partition_id):
        self._etcd = etcd
        self._data_source = data_source
        self._partition_id = partition_id
        self._make_directory_if_nessary()
        super(RawDataManager, self).__init__(
                self._raw_data_dir(), RawDataIndexSuffix, True
            )
        self._raw_data_manifest = None
        self._sync_raw_data_manifest()
        next_process_index = self._raw_data_manifest.next_process_index
        assert len(self._index_metas) <= next_process_index
        self._index_metas = self._index_metas[0: next_process_index]

    def check_index_meta_by_process_index(self, process_index):
        with self._lock:
            if process_index < 0:
                raise IndexError("{} is out of range".format(process_index))
            if self._raw_data_manifest.next_process_index > process_index:
                return True
            self._sync_raw_data_manifest()
            return self._raw_data_manifest.next_process_index > process_index

    def _get_manifest_etcd_key(self):
        return '/'.join([self._data_source.data_source_meta.name,
                        'raw_data_dir',
                        'partition_{}'.format(self._partition_id)])

    def _new_index_meta(self, process_index, start_index):
        assert self._raw_data_manifest is not None
        if process_index < self._raw_data_manifest.next_process_index:
            unindex_fname = visitor.encode_unindex_fname(
                    process_index, RawDataUnIndexSuffix
                )
            index_fname = visitor.encode_index_fname(
                    process_index, start_index, RawDataIndexSuffix
                )
            unindex_fpath = os.path.join(self._raw_data_dir(), unindex_fname)
            index_fpath = os.path.join(self._raw_data_dir(), index_fname)
            if not gfile.Exists(index_fpath):
                try:
                    if gfile.Exists(unindex_fpath):
                        gfile.Rename(unindex_fpath, index_fpath)
                except tf.errors.OpError as e:
                    logging.warning('exception with %s during index %d, %d',
                                    e, process_index, start_index)
            if not gfile.Exists(index_fpath):
                logging.fatal("Logic Error! %s not exist in %s",
                              index_fname, self._raw_data_dir())
                os._exit(-1) # pylint: disable=protected-access
            return visitor.IndexMeta(process_index, start_index, index_fpath)
        return None

    def _raw_data_dir(self):
        return os.path.join(self._data_source.raw_data_dir,
                            'partition_{}'.format(self._partition_id))

    def _sync_raw_data_manifest(self):
        etcd_key = self._get_manifest_etcd_key()
        data = self._etcd.get_data(etcd_key)
        if data is None:
            self._raw_data_manifest = dj_pb.RawDataManifest(
                    partition_id=self._partition_id
                )
        else:
            self._raw_data_manifest = text_format.Parse(
                    data, dj_pb.RawDataManifest()
                )
        return self._raw_data_manifest

    def _make_directory_if_nessary(self):
        raw_data_dir = self._raw_data_dir()
        if not gfile.Exists(raw_data_dir):
            gfile.MakeDirs(raw_data_dir)
        if not gfile.IsDirectory(raw_data_dir):
            logging.fatal("%s should be directory", raw_data_dir)
            os._exit(-1) # pylint: disable=protected-access

class RawDataVisitor(visitor.Visitor):
    def __init__(self, etcd, data_source, partition_id, raw_data_options):
        super(RawDataVisitor, self).__init__(
                "raw_data_visitor",
                RawDataManager(etcd, data_source, partition_id)
            )
        self._raw_data_options = raw_data_options

    def active_visitor(self):
        if self.is_visitor_stale():
            self._finished = False

    def _new_iter(self):
        return create_raw_data_iter(self._raw_data_options)
