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
import threading
import time

from contextlib import contextmanager

from fedlearner.data_join.raw_data_visitor import RawDataVisitor
from fedlearner.data_join.example_id_visitor import ExampleIdVisitor
from fedlearner.data_join.data_block_manager import (
    DataBlockBuilder, DataBlockManager
)

class ExampleJoiner(object):
    def __init__(self, example_joiner_options, raw_data_options,
                 etcd, data_source, partition_id):
        self._lock = threading.Lock()
        self._example_joiner_options = example_joiner_options
        self._raw_data_options = raw_data_options
        self._data_source = data_source
        self._partition_id = partition_id
        self._leader_visitor = \
                ExampleIdVisitor(etcd, self._data_source, self._partition_id)
        self._follower_visitor = \
                RawDataVisitor(etcd, self._data_source,
                               self._partition_id, raw_data_options)
        self._data_block_manager = \
                DataBlockManager(self._data_source, self._partition_id)

        self._data_block_builder = None
        self._state_stale = False
        self._follower_restart_index = 0
        self._sync_example_id_finished = False
        self._raw_data_finished = False
        self._join_finished = False
        self._latest_dump_timestamp = time.time()
        self._sync_state()

    @contextmanager
    def make_example_joiner(self):
        state_stale = self._is_state_stale()
        self._acuqire_state_stale()
        yield self._inner_joiner(state_stale)
        self._release_state_stale()

    @classmethod
    def name(cls):
        return 'BASE_EXAMPLE_JOINER'

    def get_data_block_meta_by_index(self, index):
        with self._lock:
            manager = self._data_block_manager
            return self._join_finished, \
                    manager.get_data_block_meta_by_index(index)

    def get_dumped_data_block_count(self):
        return self._data_block_manager.get_dumped_data_block_count()

    def is_join_finished(self):
        with self._lock:
            return self._join_finished

    def set_sync_example_id_finished(self):
        with self._lock:
            self._sync_example_id_finished = True

    def set_raw_data_finished(self):
        with self._lock:
            self._raw_data_finished = True

    def is_sync_example_id_finished(self):
        with self._lock:
            return self._sync_example_id_finished

    def is_raw_data_finished(self):
        with self._lock:
            return self._raw_data_finished

    def need_join(self):
        with self._lock:
            if self._join_finished:
                return False
            if self._state_stale or self._sync_example_id_finished:
                return True
            if self._follower_visitor.is_visitor_stale() or \
                    self._leader_visitor.is_visitor_stale():
                return True
            if not self._follower_visitor.finished() and \
                    not self._leader_visitor.finished():
                return True
            return self._need_finish_data_block_since_interval()

    def _inner_joiner(self, reset_state):
        raise NotImplementedError(
                "_inner_joiner not implement for base class: %s" %
                ExampleJoiner.name()
            )

    def _is_state_stale(self):
        with self._lock:
            return self._state_stale

    def _active_visitors(self):
        self._leader_visitor.active_visitor()
        self._follower_visitor.active_visitor()

    def _sync_state(self):
        meta = self._data_block_manager.get_lastest_data_block_meta()
        if meta is not None:
            try:
                self._leader_visitor.seek(meta.leader_end_index)
            except StopIteration:
                logging.warning("leader visitor finished")
            try:
                self._follower_visitor.seek(meta.follower_restart_index)
            except StopIteration:
                logging.warning("follower visitor finished")
        else:
            self._leader_visitor.reset()
            self._follower_visitor.reset()

    def _get_data_block_builder(self, create_if_no_existed):
        if self._data_block_builder is None and create_if_no_existed:
            data_block_index = \
                    self._data_block_manager.get_dumped_data_block_count()
            self._data_block_builder = DataBlockBuilder(
                    self._data_source.data_block_dir,
                    self._data_source.data_source_meta.name,
                    self._partition_id,
                    data_block_index,
                    self._example_joiner_options.data_block_dump_threshold
                )
            self._data_block_builder.set_data_block_manager(
                    self._data_block_manager
                )
            self._data_block_builder.set_follower_restart_index(
                    self._follower_restart_index
                )
        return self._data_block_builder

    def _finish_data_block(self):
        if self._data_block_builder is not None:
            meta = self._data_block_builder.finish_data_block()
            self._reset_data_block_builder()
            self._update_latest_dump_timestamp()
            return meta
        return None

    def _reset_data_block_builder(self):
        builder = None
        with self._lock:
            builder = self._data_block_builder
            self._data_block_builder = None
        if builder is not None:
            del builder

    def _update_latest_dump_timestamp(self):
        with self._lock:
            self._latest_dump_timestamp = time.time()

    def _acuqire_state_stale(self):
        with self._lock:
            self._state_stale = True

    def _release_state_stale(self):
        with self._lock:
            self._state_stale = False

    def _set_join_finished(self):
        with self._lock:
            self._join_finished = True

    def _need_finish_data_block_since_interval(self):
        dump_interval = self._example_joiner_options.data_block_dump_interval
        duration_since_dump = time.time() - self._latest_dump_timestamp
        return 0 < dump_interval <= duration_since_dump
