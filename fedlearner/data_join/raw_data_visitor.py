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

from google.protobuf import text_format

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import visitor, common
from fedlearner.data_join.raw_data_iter_impl import create_raw_data_iter

class RawDataManager(visitor.IndexMetaManager):
    def __init__(self, etcd, data_source, partition_id):
        self._etcd = etcd
        self._data_source = data_source
        self._partition_id = partition_id
        self._manifest = self._sync_raw_data_manifest()
        all_metas, index_metas = self._preload_raw_data_meta()
        super(RawDataManager, self).__init__(
                index_metas[:self._manifest.next_process_index]
            )
        self._all_metas = all_metas

    def check_index_meta_by_process_index(self, process_index):
        with self._lock:
            if process_index < 0:
                raise IndexError("{} is out of range".format(process_index))
            self._manifest = self._sync_raw_data_manifest()
            return self._manifest.next_process_index > process_index

    def _new_index_meta(self, process_index, start_index):
        if self._manifest.next_process_index <= process_index:
            return None
        raw_data_meta = None
        if process_index < len(self._all_metas):
            assert process_index == self._all_metas[process_index][0], \
                "process index should equal {} != {}".format(
                    process_index, self._all_metas[process_index][0]
                )
            raw_data_meta = self._all_metas[process_index][1]
        else:
            assert process_index == len(self._all_metas), \
                "the process index should be the next all metas "\
                "{}(process_index) != {}(size of all_metas)".format(
                        process_index, len(self._all_metas)
                    )
            raw_data_meta = self._sync_raw_data_meta(process_index)
            if raw_data_meta is None:
                logging.fatal("the raw data of partition %d index with "\
                              "%d must in etcd",
                              self._partition_id, process_index)
                os._exit(-1) # pylint: disable=protected-access
            self._all_metas.append((process_index, raw_data_meta))
        if raw_data_meta.start_index == -1:
            new_meta = dj_pb.RawDataMeta(
                    file_path=raw_data_meta.file_path,
                    start_index=start_index
                )
            odata = text_format.MessageToString(raw_data_meta)
            ndata = text_format.MessageToString(new_meta)
            etcd_key = common.raw_data_meta_etcd_key(
                    self._data_source.data_source_meta.name,
                    self._partition_id, process_index
                )

            if not self._etcd.cas(etcd_key, odata, ndata):
                raw_data_meta = self._sync_raw_data_meta(process_index)
                assert raw_data_meta is not None, \
                    "the raw data meta of process index {} "\
                    "must not None".format(process_index)
                if raw_data_meta.start_index != start_index:
                    logging.fatal("raw data of partition %d index with "\
                                  "%d must start with %d",
                                  self._partition_id, process_index,
                                  start_index)
                    os._exit(-1) # pylint: disable=protected-access
        return visitor.IndexMeta(process_index, start_index,
                                 raw_data_meta.file_path)

    def _sync_raw_data_meta(self, process_index):
        etcd_key = common.raw_data_meta_etcd_key(
                self._data_source.data_source_meta.name,
                self._partition_id, process_index
            )
        data = self._etcd.get_data(etcd_key)
        if data is not None:
            return text_format.Parse(data, dj_pb.RawDataMeta())
        return None

    def _sync_raw_data_manifest(self):
        etcd_key = common.partition_manifest_etcd_key(
                self._data_source.data_source_meta.name,
                self._partition_id
            )
        data = self._etcd.get_data(etcd_key)
        assert data is not None, "manifest must be existed"
        return text_format.Parse(data, dj_pb.RawDataManifest())

    def _preload_raw_data_meta(self):
        manifest_etcd_key = common.partition_manifest_etcd_key(
                self._data_source.data_source_meta.name,
                self._partition_id
            )
        all_metas = []
        index_metas = []
        for key, val in self._etcd.get_prefix_kvs(manifest_etcd_key, True):
            bkey = os.path.basename(key)
            if not bkey.decode().startswith(common.RawDataMetaPrefix):
                continue
            index = int(bkey[len(common.RawDataMetaPrefix):])
            meta = text_format.Parse(val, dj_pb.RawDataMeta())
            all_metas.append((index, meta))
            if meta.start_index != -1:
                index_meta = visitor.IndexMeta(index, meta.start_index,
                                               meta.file_path)
                index_metas.append(index_meta)
        all_metas = sorted(all_metas, key=lambda meta: meta[0])
        for process_index, meta in enumerate(all_metas):
            if process_index != meta[0]:
                logging.fatal("process_index mismatch with index %d != %d "\
                              "for file path %s", process_index, meta[0],
                              meta[1].file_path)
                os._exit(-1) # pylint: disable=protected-access
        return all_metas, index_metas

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
