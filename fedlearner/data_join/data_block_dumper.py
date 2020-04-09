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

from fedlearner.data_join.raw_data_visitor import RawDataVisitor
from fedlearner.data_join.data_block_manager import (
    DataBlockBuilder, DataBlockManager
)

class DataBlockDumperManager(object):
    def __init__(self, etcd, data_source, partition_id, raw_data_options):
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._data_block_manager = \
                DataBlockManager(data_source, partition_id)
        self._raw_data_visitor = \
                RawDataVisitor(etcd, data_source,
                               partition_id, raw_data_options)
        self._next_data_block_index = \
                self._data_block_manager.get_dumped_data_block_count()
        self._fly_data_block_meta = []
        self._state_stale = False
        self._synced_data_block_meta_finished = False

    def get_next_data_block_index(self):
        with self._lock:
            return self._next_data_block_index

    def get_dumped_data_block_index(self):
        return self._data_block_manager.get_dumped_data_block_count() - 1

    def add_synced_data_block_meta(self, meta):
        with self._lock:
            if self._synced_data_block_meta_finished:
                raise RuntimeError(
                        "data block dmuper manager has been mark as "\
                        "no more data block meta"
                    )
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
            return len(self._fly_data_block_meta) > 0

    def is_synced_data_block_meta_finished(self):
        with self._lock:
            return self._synced_data_block_meta_finished

    @contextmanager
    def make_data_block_dumper(self):
        self._sync_with_data_block_manager()
        self._acquire_state_stale()
        yield self._dump_data_blocks
        self._release_state_stale()

    def _dump_data_blocks(self):
        while self.need_dump():
            meta = self._get_next_data_block_meta()
            if meta is not None:
                self._raw_data_visitor.active_visitor()
                self._dump_data_block_by_meta(meta)

    def data_block_meta_sync_finished(self):
        with self._lock:
            return self._synced_data_block_meta_finished

    def _acquire_state_stale(self):
        with self._lock:
            self._state_stale = True

    def _release_state_stale(self):
        with self._lock:
            self._state_stale = False

    def _get_next_data_block_meta(self):
        with self._lock:
            if len(self._fly_data_block_meta) == 0:
                return None
            return self._fly_data_block_meta[0]

    @contextmanager
    def _make_data_block_builder(self, meta):
        assert self._partition_id == meta.partition_id, \
            "partition id of building data block meta mismatch "\
            "{} != {}".format(self._partition_id, meta.partition_id)
        builder = None
        expt = None
        try:
            builder = \
                    DataBlockBuilder(self._data_source.data_block_dir,
                                     self._data_source.data_source_meta.name,
                                     self._partition_id,
                                     meta.data_block_index)
            builder.init_by_meta(meta)
            builder.set_data_block_manager(self._data_block_manager)
            yield builder
        except Exception as e: # pylint: disable=broad-except
            logging.warning("Failed make data block builder, " \
                             "reason %s", e)
            expt = e
        if builder is not None:
            del builder
        if expt is not None:
            raise expt

    def _dump_data_block_by_meta(self, meta):
        assert meta is not None, "input data block must not be None"
        with self._make_data_block_builder(meta) as data_block_builder:
            try:
                if meta.leader_start_index == 0:
                    self._raw_data_visitor.reset()
                else:
                    assert meta.leader_start_index > 0, \
                        "leader start index must be positive"
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
                logging.fatal(
                        "Data lose corrupt! only match %d/%d example "
                        "for data block %s",
                        match_index, example_num, meta.block_id
                    )
                os._exit(-1) # pylint: disable=protected-access
            dumped_meta = data_block_builder.finish_data_block()
            assert dumped_meta == meta, "the generated dumped meta shoud "\
                                        "be the same with input mata"
            with self._lock:
                assert self._fly_data_block_meta[0] == meta
                self._fly_data_block_meta.pop(0)

    def _is_state_stale(self):
        with self._lock:
            return self._state_stale

    def _sync_with_data_block_manager(self):
        if self._is_state_stale():
            self._evict_dumped_data_block_meta()

    def _evict_dumped_data_block_meta(self):
        next_data_block_index = \
                self._data_block_manager.get_dumped_data_block_count()
        with self._lock:
            skip_count = 0
            for meta in self._fly_data_block_meta:
                if meta.data_block_index >= next_data_block_index:
                    break
                skip_count += 1
            self._fly_data_block_meta = \
                    self._fly_data_block_meta[skip_count:]
