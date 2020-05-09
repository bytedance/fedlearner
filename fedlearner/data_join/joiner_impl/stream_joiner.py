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

import fedlearner.data_join.common as common
from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner

class JoinWindow(object):
    def __init__(self, pt_rate, qt_rate):
        assert 0.0 <= pt_rate <= 1.0, \
            "pt_rate {} should in [0.0, 1.0]".format(pt_rate)
        assert 0.0 <= qt_rate <= 1.0, \
            "qt_rate {} should in [0.0, 1.0]".format(qt_rate)
        self._buffer = []
        self._event_time = []
        self._event_time_sorted = True
        self._pt_rate = pt_rate
        self._qt_rate = qt_rate
        self._committed_pt = None

    def __iter__(self):
        return iter(self._buffer)

    def append(self, index, item):
        if len(self._event_time) > 0 and \
                self._event_time[-1] > item.event_time:
            self._event_time_sorted = False
        self._buffer.append((index, item))
        self._event_time.append(item.event_time)

    def size(self):
        return len(self._buffer)

    def forward_pt(self):
        if len(self._buffer) == 0:
            return False
        new_pt = self._cal_pt(self._pt_rate)
        if self._committed_pt is None or new_pt > self._committed_pt:
            self._committed_pt = new_pt
            return True
        return False

    def committed_pt(self):
        return self._committed_pt

    def qt(self):
        return self._cal_pt(self._qt_rate)

    def reset(self, new_buffer, state_stale):
        even_times = []
        for _, item in new_buffer:
            even_times.append(item.event_time)
        self._buffer = new_buffer
        self._event_time = even_times
        if state_stale:
            self._committed_pt = None
        self._event_time_sorted = len(new_buffer) == 0

    def __getitem__(self, index):
        return self._buffer[index]

    def _cal_pt(self, rate):
        if not self._buffer:
            return None
        if not self._event_time_sorted:
            self._event_time.sort()
            self._event_time_sorted = True
        pos = int(len(self._event_time) * rate)
        if pos == len(self._buffer):
            pos = len(self._buffer) - 1
        return self._event_time[pos]

class StreamExampleJoiner(ExampleJoiner):
    def __init__(self, example_joiner_options, raw_data_options,
                 data_block_builder_options, etcd, data_source, partition_id):
        super(StreamExampleJoiner, self).__init__(example_joiner_options,
                                                  raw_data_options,
                                                  data_block_builder_options,
                                                  etcd, data_source,
                                                  partition_id)
        self._min_window_size = example_joiner_options.min_matching_window
        self._max_window_size = example_joiner_options.max_matching_window
        self._leader_join_window = JoinWindow(0.05, 0.99)
        self._follower_join_window = JoinWindow(0.05, 0.90)
        self._joined_cache = {}
        self._leader_unjoined_example_ids = []
        self._follower_example_cache = {}
        self._fill_leader_enough = False
        self._reset_joiner_state(True)

    @classmethod
    def name(cls):
        return 'STREAM_JOINER'

    def _inner_joiner(self, state_stale):
        if self.is_join_finished():
            return
        sync_example_id_finished, raw_data_finished = \
                self._prepare_join(state_stale)
        while self._fill_leader_join_window(sync_example_id_finished) and \
                self._leader_join_window.size() > 0:
            delay_dump = True
            while delay_dump and \
                    self._fill_follower_join_window(raw_data_finished):
                delay_dump = self._need_delay_dump(raw_data_finished)
                if delay_dump:
                    self._update_join_cache()
                else:
                    for (li, le) in self._leader_join_window:
                        eid = le.example_id
                        if eid not in self._follower_example_cache and \
                                eid not in self._joined_cache:
                            continue
                        if eid not in self._joined_cache:
                            self._joined_cache[eid] = \
                                    self._follower_example_cache[eid]
                        builder = self._get_data_block_builder(True)
                        assert builder is not None, \
                            "data block builder must be not "\
                            "None if before dummping"
                        fi, item = self._joined_cache[eid]
                        et = le.event_time
                        builder.append_item(item, eid, et, li, fi)
                        if builder.check_data_block_full():
                            yield self._finish_data_block()
                self._evit_stale_follower_cache()
            if not delay_dump:
                self._reset_joiner_state(False)
            else:
                break
        join_data_finished = sync_example_id_finished and raw_data_finished
        if self._get_data_block_builder(False) is not None and \
                (self._need_finish_data_block_since_interval() or
                    join_data_finished):
            yield self._finish_data_block()
        if join_data_finished:
            self._set_join_finished()
            logging.warning("finish join example for partition %d by %s",
                            self._partition_id, self.name())

    def _prepare_join(self, state_stale):
        if state_stale:
            self._reset_joiner_state(True)
        return super(StreamExampleJoiner, self)._prepare_join(state_stale)

    def _need_delay_dump(self, raw_data_finished):
        if self._follower_visitor.finished() and raw_data_finished:
            return False
        leader_qt = self._leader_join_window.qt()
        follower_qt = self._follower_join_window.qt()
        if leader_qt is not None and follower_qt is not None and \
                follower_qt >= leader_qt:
            return False
        return True

    def _update_join_cache(self):
        new_unjoined_example_ids = []
        for example_id in self._leader_unjoined_example_ids:
            if example_id in self._follower_example_cache:
                self._joined_cache[example_id] = \
                        self._follower_example_cache[example_id]
            else:
                new_unjoined_example_ids.append(example_id)
        self._leader_unjoined_example_ids = new_unjoined_example_ids

    def _reset_joiner_state(self, state_stale):
        self._leader_join_window.reset([], state_stale)
        self._fill_leader_enough = False
        self._joined_cache = {}
        self._leader_unjoined_example_ids = []
        if state_stale:
            self._follower_join_window.reset([], True)
            self._follower_example_cache = {}

    def _fill_leader_join_window(self, sync_example_id_finished):
        if self._fill_leader_enough:
            return True
        if not self._fill_join_windows(self._leader_visitor,
                                       self._leader_join_window,
                                       None):
            self._fill_leader_enough = sync_example_id_finished
        else:
            self._fill_leader_enough = True
        if self._fill_leader_enough:
            self._leader_unjoined_example_ids = []
            for _, item in self._leader_join_window:
                self._leader_unjoined_example_ids.append(item.example_id)
        return self._fill_leader_enough

    def _fill_follower_join_window(self, raw_data_finished):
        if not self._fill_join_windows(self._follower_visitor,
                                       self._follower_join_window,
                                       self._follower_example_cache):
            return raw_data_finished
        return True

    def _fill_join_windows(self, visitor, join_window, join_cache):
        while not visitor.finished() and \
                join_window.size() < self._max_window_size:
            required_item_count = self._min_window_size
            if join_window.size() >= self._min_window_size:
                required_item_count *= 2
            if required_item_count >= self._max_window_size:
                required_item_count = self._max_window_size
            self._consume_item_until_count(
                    visitor, join_window,
                    required_item_count, join_cache
                )
            if join_window.forward_pt():
                return True
        return join_window.size() >= self._max_window_size

    def _evict_if_useless(self, item):
        return item.example_id in self._joined_cache or \
                item.event_time < self._leader_join_window.committed_pt()

    def _evict_if_force(self, item):
        return item.event_time < self._leader_join_window.qt()

    def _evict_impl(self, candidates, filter_fn):
        reserved_items = []
        for (index, item) in candidates:
            example_id = item.example_id
            if filter_fn(item):
                self._follower_example_cache.pop(example_id, None)
            else:
                reserved_items.append((index, item))
        return reserved_items

    def _evit_stale_follower_cache(self):
        reserved_items = self._evict_impl(self._follower_join_window,
                                          self._evict_if_useless)
        if len(reserved_items) < self._max_window_size:
            self._follower_join_window.reset(reserved_items, False)
            return
        reserved_items = self._evict_impl(reserved_items,
                                          self._evict_if_force)
        self._follower_join_window.reset(reserved_items, False)

    def _consume_item_until_count(self, visitor, windows,
                                  required_item_count, cache=None):
        for (index, item) in visitor:
            if item.example_id == common.InvalidExampleId:
                logging.warning("ignore item indexed as %d from %s since "\
                                "invalid example id", index, visitor.name())
            elif item.event_time == common.InvalidEventTime:
                logging.warning("ignore item indexed as %d from %s since "\
                                "invalid event time", index, visitor.name())
            else:
                windows.append(index, item)
                if cache is not None:
                    cache[item.example_id] = (index, item)
                if windows.size() >= required_item_count:
                    return
        assert visitor.finished(), "visitor shoud be finished of "\
                                   "required_item is not satisfied"

    def _finish_data_block(self):
        meta = super(StreamExampleJoiner, self)._finish_data_block()
        self._follower_restart_index = self._follower_visitor.get_index()
        if self._follower_join_window.size() > 0:
            self._follower_restart_index = \
                    self._follower_join_window[0][0]
        for index, _ in self._joined_cache.values():
            if index < self._follower_restart_index:
                self._follower_restart_index = index
        return meta
