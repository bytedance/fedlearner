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
import time
import traceback
from contextlib import contextmanager
from collections import defaultdict

from fedlearner.common import metrics
from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.raw_data_visitor import RawDataVisitor
from fedlearner.data_join.data_block_manager import \
        DataBlockManager, DataBlockBuilder
from fedlearner.data_join import common


class DataBlockDumperManager(object):
    def __init__(self, kvstore, data_source, partition_id,
                 raw_data_options, data_block_builder_options):
        """
        self._optional_stats:
        Counters for optional stats, will count total joined num and total num
            of different values of every stat field.
            E.g., for stat field='label', the values of field `label` will be
            0(positive example) and 1(negative_example):
        {
            'joined': {
                # '__None__' for examples without label field
                'label': {1: 123, 0: 345, '__None__': 45},
                'other_field': {...},
                ...
            },
            'total': {
                'label': {1: 234, 0: 456, '__None__': 56}
                'other_field': {...},
                ...
            }
        }
        Will only count follower examples here as no fields are transmitted from
            leader other than lite example_id.
        """
        self._lock = threading.Lock()
        self._data_source = data_source
        self._partition_id = partition_id
        self._data_block_manager = \
                DataBlockManager(data_source, partition_id)
        self._raw_data_visitor = \
                RawDataVisitor(kvstore, data_source,
                               partition_id, raw_data_options)
        self._data_block_builder_options = data_block_builder_options
        self._next_data_block_index = \
                self._data_block_manager.get_dumped_data_block_count()
        meta = self._data_block_manager.get_lastest_data_block_meta()
        self._optional_stats_fields = raw_data_options.optional_stats_fields
        if meta is None:
            self._optional_stats = {
                'joined': {stat_field: defaultdict(int)
                           for stat_field in self._optional_stats_fields},
                'total': {stat_field: defaultdict(int)
                          for stat_field in self._optional_stats_fields}
            }
        else:
            stats_info = meta.joiner_stats_info
            self._optional_stats = {
                'joined': {field: defaultdict(
                    int, stats_info.joined_optional_stats[field].counter)
                    for field in stats_info.joined_optional_stats},
                'total': {field: defaultdict(
                    int, stats_info.total_optional_stats[field].counter)
                    for field in stats_info.joined_optional_stats}
            }
        self._fly_data_block_meta = []
        self._state_stale = False
        self._synced_data_block_meta_finished = False
        ds_name = self._data_source.data_source_meta.name
        self._metrics_tags = {'data_source_name': ds_name,
                              'partition': self._partition_id}

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
                start_tm = time.time()
                self._raw_data_visitor.active_visitor()
                self._dump_data_block_by_meta(meta)
                dump_duration = time.time() - start_tm
                metrics.emit_timer(name='data_block_dump_duration',
                                   value=int(dump_duration),
                                   tags=self._metrics_tags)

    def data_block_meta_sync_finished(self):
        with self._lock:
            return self._synced_data_block_meta_finished

    def _update_stats(self, item, kind='joined'):
        """
        optional_stats[field] retrieve the counter of field (e.g. 'label')
        [optional_stats[field]] retrieved the count value
        For field='label', [optional_stats[field]] += 1 will increment the
            count of specific `kind` of positive examples (value == 1)
            if optional_stats[field] == 1, else the neg count if the value == 0,
            else the '__None__' (examples without 'label' field) count
        """
        if item.optional_stats == common.NonExistentStats:
            return
        for field in self._optional_stats_fields:
            self._optional_stats[kind][field][item.optional_stats[field]] += 1

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
            builder = DataBlockBuilder(
                    common.data_source_data_block_dir(self._data_source),
                    self._data_source.data_source_meta.name,
                    self._partition_id,
                    meta.data_block_index,
                    self._data_block_builder_options
                )
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
                traceback.print_stack()
                os._exit(-1) # pylint: disable=protected-access
            match_index = 0
            example_num = len(meta.example_ids)
            need_match = True
            for (index, item) in self._raw_data_visitor:
                self._update_stats(item, kind='total')
                example_id = item.example_id
                # ELements in meta.example_ids maybe duplicated
                while need_match and match_index < example_num and \
                        example_id == meta.example_ids[match_index]:
                    data_block_builder.write_item(item)
                    self._update_stats(item, kind='joined')
                    match_index += 1
                if match_index >= example_num:
                    # if no need to get the total num of examples, break
                    # else iterate raw data without matching
                    if len(self._optional_stats_fields) == 0:
                        break
                    else:
                        need_match = False
                if index >= meta.leader_end_index:
                    break
            if match_index < example_num:
                logging.fatal(
                        "Data lose corrupt! only match %d/%d example "
                        "for data block %s",
                        match_index, example_num, meta.block_id
                    )
                traceback.print_stack()
                os._exit(-1) # pylint: disable=protected-access
            data_block_builder.set_join_stats_info(
                self._create_stats_info()
            )
            dumped_meta = data_block_builder.finish_data_block(
                True, self._metrics_tags
            )
            dumped_meta.joiner_stats_info.joined_optional_stats.clear()
            dumped_meta.joiner_stats_info.total_optional_stats.clear()
            assert dumped_meta == meta, "the generated dumped meta should "\
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

    def _create_stats_info(self):
        joined_map, total_map = {}, {}
        if len(self._optional_stats_fields) > 0:
            for field, counter in self._optional_stats['joined'].items():
                joined_map[field] = dj_pb.OptionalStatCounter(counter=counter)
            for field, counter in self._optional_stats['total'].items():
                total_map[field] = dj_pb.OptionalStatCounter(counter=counter)
        return dj_pb.JoinerStatsInfo(
                joined_optional_stats=joined_map,
                total_optional_stats=total_map
            )
