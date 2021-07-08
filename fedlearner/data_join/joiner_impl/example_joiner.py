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

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import metrics
from fedlearner.data_join import common
from fedlearner.data_join.data_block_manager import \
    DataBlockManager, DataBlockBuilder
from fedlearner.data_join.example_id_visitor import ExampleIdVisitor
from fedlearner.data_join.joiner_impl.joiner_stats import JoinerStats
from fedlearner.data_join.joiner_impl.optional_stats import OptionalStats
from fedlearner.data_join.raw_data_visitor import RawDataVisitor


class ExampleJoiner(object):
    def __init__(self, example_joiner_options, raw_data_options,
                 data_block_builder_options, kvstore, data_source,
                 partition_id):
        self._lock = threading.Lock()
        self._example_joiner_options = example_joiner_options
        self._raw_data_options = raw_data_options
        self._data_source = data_source
        self._partition_id = partition_id
        self._leader_visitor = \
                ExampleIdVisitor(kvstore, self._data_source, self._partition_id)
        self._follower_visitor = \
                RawDataVisitor(kvstore, self._data_source,
                               self._partition_id, raw_data_options)
        self._data_block_manager = \
                DataBlockManager(self._data_source, self._partition_id)
        meta = self._data_block_manager.get_lastest_data_block_meta()
        if meta is None:
            self._joiner_stats = JoinerStats(0, -1, -1)
        else:
            stats_info = meta.joiner_stats_info
            self._joiner_stats = JoinerStats(stats_info.stats_cum_join_num,
                                             stats_info.leader_stats_index,
                                             stats_info.follower_stats_index)
        self._data_block_builder_options = data_block_builder_options
        self._data_block_builder = None
        self._state_stale = False
        self._follower_restart_index = 0
        self._sync_example_id_finished = False
        self._raw_data_finished = False
        self._join_finished = False
        ds_name = self._data_source.data_source_meta.name
        self._metrics_tags = {'data_source_name': ds_name,
                              'partition': partition_id,
                              'joiner_name': self.name()}
        self._optional_stats = OptionalStats(
            raw_data_options, self._metrics_tags)
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

    def _prepare_join(self, state_stale):
        if state_stale:
            self._sync_state()
            self._reset_data_block_builder()
        sync_example_id_finished = self.is_sync_example_id_finished()
        raw_data_finished = self.is_raw_data_finished()
        self._active_visitors()
        return sync_example_id_finished, raw_data_finished

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
                self._follower_restart_index = meta.follower_restart_index
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
                    common.data_source_data_block_dir(self._data_source),
                    self._data_source.data_source_meta.name,
                    self._partition_id,
                    data_block_index,
                    self._data_block_builder_options,
                    self._example_joiner_options.data_block_dump_threshold
                )
            self._data_block_builder.set_data_block_manager(
                    self._data_block_manager
                )
        if self._data_block_builder:
            self._data_block_builder.set_follower_restart_index(
                self._follower_restart_index
            )
        return self._data_block_builder

    def _finish_data_block(self):
        if self._data_block_builder is not None:
            self._data_block_builder.set_join_stats_info(
                    self._create_join_stats_info()
                )
            meta = self._data_block_builder.finish_data_block(
                    True, self._metrics_tags
                )
            self._optional_stats.emit_optional_stats()
            self._reset_data_block_builder()
            self._update_latest_dump_timestamp()
            return meta
        return None

    def _create_join_stats_info(self):
        builder = self._get_data_block_builder(False)
        nstats_cum_join_num = self._joiner_stats.calc_stats_joined_num()
        nactual_cum_join_num = 0 if builder is None \
                               else builder.example_count()
        meta = self._data_block_manager.get_lastest_data_block_meta()
        if meta is not None:
            nactual_cum_join_num += meta.joiner_stats_info.actual_cum_join_num
        return dj_pb.JoinerStatsInfo(
            stats_cum_join_num=nstats_cum_join_num,
            actual_cum_join_num=nactual_cum_join_num,
            leader_stats_index=self._joiner_stats.get_leader_stats_index(),
            follower_stats_index=self._joiner_stats.get_follower_stats_index()
        )

    def _reset_data_block_builder(self):
        builder = None
        with self._lock:
            builder = self._data_block_builder
            self._data_block_builder = None
        if builder is not None:
            del builder

    def _update_latest_dump_timestamp(self):
        data_block_dump_duration = time.time() - self._latest_dump_timestamp
        metrics.emit_timer(name='data_block_dump_duration',
                           value=int(data_block_dump_duration),
                           tags=self._metrics_tags)
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
