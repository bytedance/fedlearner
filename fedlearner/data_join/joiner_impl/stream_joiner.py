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

from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner

class StreamExampleJoiner(ExampleJoiner):
    def __init__(self, etcd, data_source, partition_id, options):
        super(StreamExampleJoiner, self).__init__(
                etcd, data_source, partition_id, options
            )
        self._leader_left_pt = None
        self._leader_right_pt = None
        self._follower_left_pt = None
        self._follower_right_pt = None
        self._min_window_size = data_source.data_source_meta.min_matching_window
        self._max_window_size = data_source.data_source_meta.max_matching_window
        self._leader_join_window = []
        self._follower_join_cache = {}

    @classmethod
    def name(cls):
        return 'STREAM_JOINER'

    def join_example(self):
        if self._data_block_manager.join_finished():
            return
        if self._stale_with_dfs:
            self._sync_state()
        self._leader_left_pt = None
        self._leader_right_pt = None
        self._follower_left_pt = None
        self._follower_right_pt = None
        self._leader_join_window = []
        self._follower_join_cache = {}

        try:
            while not self._leader_visitor.finished():
                self._load_leader_join_windows()
                self._update_follower_join_cache()
                self._join_impl()
                self._evit_stale_follower_cache()
            builder = self._get_data_block_builder()
            if builder is not None:
                self._finish_data_block()
        except Exception as e: # pylint: disable=broad-except
            logging.error("meet exception during example join %s", e)
            self._stale_with_dfs = True
            self._data_block_builder = None
        else:
            logging.warning("Finish data join for partition %d",
                            self._partition_id)
            self._data_block_manager.finish_join()

    def _load_leader_join_windows(self):
        self._leader_join_window = []
        event_time = []
        example_num = self._min_window_size
        while not self._leader_visitor.finished():
            self._load_example_until_number(
                    self._leader_visitor, self._leader_join_window,
                    event_time, example_num
                )
            assert len(event_time) == len(self._leader_join_window)
            if len(self._leader_join_window) == 0:
                break
            new_leader_left_pt = self._percentile_pt(event_time, 0.05)
            self._leader_right_pt = self._percentile_pt(event_time, 1.0)
            if (self._leader_left_pt is None or
                    new_leader_left_pt > self._leader_left_pt):
                self._leader_left_pt = new_leader_left_pt
                break
            if example_num >= self._max_window_size:
                break
            example_num *= 2
            if example_num > self._max_window_size:
                example_num = self._max_window_size

    def _update_follower_join_cache(self):
        follower_join_window = []
        event_time = []
        example_num = self._min_window_size
        while (not self._follower_visitor.finished() and
                len(self._leader_join_window) > 0):
            assert self._leader_left_pt is not None
            assert self._leader_right_pt is not None
            if len(follower_join_window) >= self._max_window_size:
                new_join_window = []
                new_event_time = []
                for (idx, et) in enumerate(event_time):
                    if et >= self._leader_left_pt:
                        new_event_time.append(et)
                        new_join_window.append(
                            follower_join_window[idx])
                follower_join_window = new_join_window
                event_time = new_event_time
            self._load_example_until_number(
                    self._follower_visitor, follower_join_window,
                    event_time, example_num
                )
            assert len(event_time) == len(follower_join_window)
            if len(event_time) == 0:
                break
            new_follower_left_pt = self._percentile_pt(event_time, 0.05)
            if (self._follower_left_pt is None or
                        new_follower_left_pt > self._follower_left_pt):
                self._follower_left_pt = new_follower_left_pt
            new_follower_right_pt = self._percentile_pt(event_time, 0.95)
            if (self._follower_left_pt >= self._leader_left_pt and
                    new_follower_right_pt >= self._leader_right_pt):
                break
            example_num *= 2
        for (index, item) in follower_join_window:
            example_id = item.example_id
            self._follower_join_cache[example_id] = (index, item)

    def _join_impl(self):
        for (li, le) in self._leader_join_window:
            example_id = le.example_id
            if example_id not in self._follower_join_cache:
                continue
            fi, item = self._follower_join_cache[example_id]
            event_time = le.event_time
            self._follower_join_cache.pop(example_id, None)
            builder = self._get_data_block_builder()
            assert builder is not None
            builder.append(item.record, example_id, event_time, li, fi)
            if builder.check_data_block_full():
                self._finish_data_block()

    def _evit_stale_follower_cache(self):
        evicted_example_ids = []
        min_follower_index = None
        for (example_id, v) in self._follower_join_cache.items():
            follower_index = v[0]
            event_time = v[1].event_time
            if event_time < self._leader_left_pt:
                evicted_example_ids.append(example_id)
            elif (min_follower_index is None or
                    min_follower_index > follower_index):
                min_follower_index = follower_index
        if min_follower_index is not None:
            assert min_follower_index >= self._follower_restart_index
            self._follower_restart_index = min_follower_index
        for example_id in evicted_example_ids:
            self._follower_join_cache.pop(example_id, None)

    def _load_example_until_number(self, visitor, cache,
                                   event_times, example_num):
        for (index, item) in visitor:
            event_time = item.event_time
            event_times.append(event_time)
            cache.append((index, item))
            if len(cache) >= example_num:
                return
        assert visitor.finished()

    @staticmethod
    def _percentile_pt(event_time_array, rate):
        event_time_array.sort()
        pos = int(len(event_time_array) * rate)
        if pos >= len(event_time_array):
            pos = len(event_time_array) - 1
        return event_time_array[pos]
