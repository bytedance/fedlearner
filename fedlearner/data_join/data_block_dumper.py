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
import logging
import os
from contextlib import contextmanager

import tensorflow as tf
from fedlearner.data_join.raw_data_visitor import RawDataVisitor
from fedlearner.data_join.data_block_manager import (
    DataBlockBuilder, DataBlockManager
)

class DataBlockDumperManager(object):
    def __init__(self, etcd, data_source, partition_id, options):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._data_block_manager = DataBlockManager(data_source, partition_id)
        self._raw_data_visitor = RawDataVisitor(
                etcd, data_source, partition_id, options
            )
        self._next_data_block_index = (
                self._data_block_manager.get_dumped_data_block_num()
            )
        self._fly_data_block_meta = []
        self._stale_with_dfs = False
        self._synced_data_block_meta_finished = False

    def get_partition_id(self):
        return self._partition_id

    def get_next_data_block_index(self):
        with self._lock:
            return self._next_data_block_index

    def append_synced_data_block_meta(self, meta):
        with self._lock:
            if self._next_data_block_index != meta.data_block_index:
                return False, self._next_data_block_index
            self._fly_data_block_meta.append(meta)
            self._next_data_block_index += 1
            return True, self._next_data_block_index

    def finish_sync_data_block_meta(self):
        with self._lock:
            self._synced_data_block_meta_finished = True

    def need_dump(self):
        with self._lock:
            return (len(self._fly_data_block_meta) > 0 or
                    self._stale_with_dfs)

    def dump_data_blocks(self):
        try:
            self._sync_with_dfs()
            while True:
                finished = False
                meta = None
                builder = None
                with self._lock:
                    finished, meta = self._get_next_data_block_meta()
                self._create_data_block_by_meta(meta)
                if meta is None:
                    return
        except Exception as e: # pylint: disable=broad-except
            logging.error("Failed to dump data block for partition "\
                          "%d with expect %s", self._partition_id, e)
            with self._lock:
                self._stale_with_dfs = True

    def data_block_meta_sync_finished(self):
        with self._lock:
            return self._synced_data_block_meta_finished

    def _get_next_data_block_meta(self):
        if len(self._fly_data_block_meta) == 0:
            if self._synced_data_block_meta_finished:
                return True, None
            return False, None
        return False, self._fly_data_block_meta[0]

    @contextmanager
    def _make_data_block_builder(self, meta):
        manager = self._data_block_manager
        assert manager is not None
        assert self._partition_id == meta.partition_id
        builder = None
        try:
            builder = DataBlockBuilder(
                    self._data_source.data_block_dir,
                    self._partition_id,
                    meta.data_block_index,
                )
            builder.init_by_meta(meta)
            yield builder
        except Exception as e: # pylint: disable=broad-except
            logging.warning(
                    "Failed make data block builder, reason %s", e
                )
        del builder

    def _create_data_block_by_meta(self, meta):
        if meta is None:
            return
        with self._make_data_block_builder(meta) as data_block_builder:
            try:
                if meta.leader_start_index == 0:
                    self._raw_data_visitor.reset()
                else:
                    assert meta.leader_start_index > 0
                    self._raw_data_visitor.seek(meta.leader_start_index-1)
            except StopIteration:
                logging.fatal("raw data finished before when seek to %d",
                              meta.leader_start_index-1)
                os._exit(-1) # pylint: disable=protected-access
            match_index = 0
            example_num = len(meta.example_ids)
            for (index, item) in self._raw_data_visitor:
                example_id = item.example_id
                if example_id == meta.example_ids[match_index]:
                    data_block_builder.append_raw_example(item.record)
                    match_index += 1
                if match_index >= example_num:
                    break
                if index >= meta.leader_end_index:
                    break
            if match_index < example_num:
                for idx in range(match_index, example_num):
                    feat = {}
                    example_id = meta.example_ids[idx]
                    feat['example_id'] = tf.train.Feature(
                            bytes_list=tf.train.BytesList(value=[example_id]))
                    empty_example = tf.train.Example(
                        features=tf.train.Features(feature=feat))
                    data_block_builder.append_raw_example(
                            empty_example.SerializeToString()
                        )
            data_block_builder.finish_data_block()
            assert meta == data_block_builder.get_data_block_meta()
            self._data_block_manager.add_dumped_data_block_meta(meta)
            with self._lock:
                assert self._fly_data_block_meta[0] == meta
                self._fly_data_block_meta.pop(0)

    def _sync_with_dfs(self):
        manager = self._data_block_manager
        dumped_num = manager.get_dumped_data_block_num(self._sync_with_dfs)
        with self._lock:
            skip_count = 0
            for meta in self._fly_data_block_meta:
                if meta.data_block_index >= dumped_num:
                    break
                skip_count += 1
            self._fly_data_block_meta = self._fly_data_block_meta[skip_count:]
