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

try:
    import queue
except ImportError:
    import Queue as queue
import logging
import threading
import os

from tensorflow.compat.v1 import gfile

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common.db_client import DBClient
from fedlearner.data_join import common, data_block_visitor, \
    raw_data_manifest_manager
from fedlearner.data_join.data_block_manager import \
    DataBlockManager, DataBlockBuilder
from fedlearner.data_join.sort_run_merger import SortRunReader


class _DataBlockWriter(object):
    def __init__(self, data_source, partition_id,
                 data_block_builder_options,
                 data_block_dump_threshold):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._data_block_builder_options = data_block_builder_options
        self._data_block_dump_threshold = data_block_dump_threshold
        self._leader_idx = 0
        self._follower_idx = 0
        self._data_block_manager = \
            DataBlockManager(self._data_source, partition_id)
        self._data_block_builder = None

    def _get_data_block_builder(self, create_if_no_existed):
        if self._data_block_builder is None and create_if_no_existed:
            data_block_index = \
                self._data_block_manager.get_dumped_data_block_count()
            self._data_block_builder = DataBlockBuilder(
                common.data_source_data_block_dir(self._data_source),
                self._data_source.data_source_meta.name,
                self._partition_id,
                data_block_index,
                self._data_block_builder_options,
                self._data_block_dump_threshold)
            self._data_block_builder.set_data_block_manager(
                self._data_block_manager
            )
            self._data_block_builder.set_follower_restart_index(
                self._follower_idx)
        return self._data_block_builder

    def _finish_data_block(self):
        if self._data_block_builder is not None:
            meta = self._data_block_builder.finish_data_block(True)
            self._reset_data_block_builder()
            return meta
        return None

    def _reset_data_block_builder(self):
        with self._lock:
            builder = self._data_block_builder
            self._data_block_builder = None
        if builder is not None:
            del builder

    def append(self, item):
        builder = self._get_data_block_builder(True)
        assert builder is not None, "data block builder must not be " \
                                    "None before dumping"
        builder.append_item(item, self._leader_idx, self._follower_idx)
        self._leader_idx += 1
        self._follower_idx += 1
        if builder.check_data_block_full():
            self._finish_data_block()

    def finish(self):
        self._finish_data_block()


class SortRunDataBlockMerger(object):
    # sort and merge the mapped original data to data blocks
    def __init__(self, options, comparator,
                 data_source_name, partition_num,
                 output_base_dir,
                 data_block_dump_threshold,
                 kvstore_type, use_mock_etcd=False):
        self._lock = threading.Lock()
        self._options = options
        self._comparator = comparator
        self._data_source_name = data_source_name
        self._partition_num = partition_num
        self._output_base_dir = output_base_dir
        self._data_block_dump_threshold = data_block_dump_threshold
        self._kvstore_type = kvstore_type
        self._use_mock_etcd = use_mock_etcd
        self._kvstore = DBClient(self._kvstore_type, self._use_mock_etcd)
        self._data_source = self._create_data_source()
        self._data_block_manager = \
            DataBlockManager(self._data_source, self._partition_id)

    def _create_data_source(self):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = self._data_source_name
        data_source.data_source_meta.partition_num = self._partition_num
        data_source.output_base_dir = self._output_base_dir
        data_source.state = common_pb.DataSourceState.Init
        data_source.role = common_pb.FLRole.Leader
        master_kvstore_key = common.data_source_kvstore_base_dir(
            data_source.data_source_meta.name
        )
        raw_data = self._kvstore.get_data(master_kvstore_key)
        if raw_data is None:
            logging.info("data source %s is not existed",
                         self._data_source_name)
            common.commit_data_source(self._kvstore, data_source)
            logging.info("apply new data source %s", self._data_source_name)
        else:
            logging.info("data source %s has been existed",
                         self._data_source_name)
        return data_source

    def merge_sort_runs(self, input_fpaths):
        if len(input_fpaths) == 0:
            logging.info("no sort run for partition %d", self._partition_id)
            return []
        dumped_item = self._sync_state()
        readers = self._create_sort_run_readers(input_fpaths)
        pque = queue.PriorityQueue(len(input_fpaths) + 1)
        for idx, reader in enumerate(readers):
            if not reader.finished():
                for item in reader:
                    if dumped_item is None or \
                            not self._comparator(item, dumped_item):
                        pque.put(item)
                        break
        writer = self._create_data_block_writer()
        while pque.qsize() > 0:
            item = pque.get()
            writer.append(item.inner_item)
            assert item.reader_index < len(readers)
            self._replenish_item(readers[item.reader_index], pque)
        writer.finish()
        self._mock_raw_data_manifest()
        return self._list_finished_fpath()

    @classmethod
    def _replenish_item(cls, reader, pque):
        if not reader.finished():
            for item in reader:
                pque.put(item)
                break

    def _create_sort_run_readers(self, input_fpaths):
        assert len(input_fpaths) > 0
        readers = []
        for index, input_fpath in enumerate(input_fpaths):
            reader = SortRunReader(index, input_fpath,
                                   self._options.reader_options,
                                   self._comparator)
            readers.append(reader)
        return readers

    def _create_data_block_writer(self):
        return _DataBlockWriter(
            self._data_source,
            self._partition_id,
            self._options.writer_options,
            self._data_block_dump_threshold)

    def _list_finished_fpath(self):
        dirpath = os.path.join(
            common.data_source_data_block_dir(self._data_source),
            common.partition_repr(self._partition_id))
        if gfile.Exists(dirpath) and gfile.IsDirectory(dirpath):
            return [os.path.join(dirpath, f) for f in \
                    gfile.ListDirectory(dirpath)
                    if f.endswith(common.DataBlockSuffix)]
        return []

    def _sync_state(self):
        meta = self._data_block_manager.get_lastest_data_block_meta()
        if meta is not None:
            visitor = data_block_visitor.DataBlockVisitor(
                self._data_source.data_source_meta.name, self._kvstore_type,
                self._use_mock_etcd
            )
            db_rep = visitor.LoadDataBlockRepByBlockId(meta.block_id)
            last_item = None
            for item in SortRunReader(0, db_rep.data_block_fpath,
                                      self._options.reader_options,
                                      self._comparator):
                last_item = item
            assert last_item is not None
            return last_item
        return None

    def _mock_raw_data_manifest(self):
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self._kvstore, self._data_source
        )
        manifest_manager.finish_sync_example_id_partition(
            dj_pb.SyncExampleIdState.UnSynced,
            dj_pb.SyncExampleIdState.Synced,
            -1, self._partition_id)
        manifest_manager.finish_join_example_partition(
            dj_pb.JoinExampleState.UnJoined,
            dj_pb.JoinExampleState.Joined,
            -1, self._partition_id)

    @property
    def _partition_id(self):
        return self._options.partition_id
