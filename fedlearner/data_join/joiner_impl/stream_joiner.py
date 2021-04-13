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
import time

import fedlearner.data_join.common as common
from fedlearner.common import metrics
from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner
from fedlearner.data_join.negative_example_generator \
    import NegativeExampleGenerator


class _CmpCtnt(object):
    def __init__(self, item):
        self._event_time = item.event_time
        self._example_id = item.example_id

    def __lt__(self, other):
        assert isinstance(other, _CmpCtnt)
        if self._event_time != other._event_time:
            return self._event_time < other._event_time
        return self._example_id < other._example_id

    def __eq__(self, other):
        assert isinstance(other, _CmpCtnt)
        return self._event_time == other._event_time and \
            self._example_id == other._example_id

    def __str__(self):
        return "%s:%s"%(self._example_id, self._event_time)


class _JoinWindow(object):
    def __init__(self, pt_rate, qt_rate):
        assert 0.0 <= pt_rate <= 1.0, \
            "pt_rate {} should in [0.0, 1.0]".format(pt_rate)
        assert 0.0 <= qt_rate <= 1.0, \
            "qt_rate {} should in [0.0, 1.0]".format(qt_rate)
        self._buffer = []
        self._cmp_ctnt = []
        self._cmp_ctnt_sorted = True
        self._pt_rate = pt_rate
        self._qt_rate = qt_rate
        self._committed_pt = None

    def __iter__(self):
        return iter(self._buffer)

    def append(self, index, item):
        if len(self._cmp_ctnt) > 0 and \
                self._cmp_ctnt[-1] > _CmpCtnt(item):
            self._cmp_ctnt_sorted = False
        self._cmp_ctnt.append(_CmpCtnt(item))
        self._buffer.append((index, item))

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
        self._cmp_ctnt = [_CmpCtnt(item[1]) for item in new_buffer]
        self._buffer = new_buffer
        if state_stale:
            self._committed_pt = None
        self._cmp_ctnt_sorted = \
                all((self._cmp_ctnt[i] < self._cmp_ctnt[i+1] or
                     self._cmp_ctnt[i] == self._cmp_ctnt[i+1])
                    for i in range(len(self._cmp_ctnt)-1))

    def __getitem__(self, index):
        return self._buffer[index]

    def _cal_pt(self, rate):
        if not self._buffer:
            return None
        if not self._cmp_ctnt_sorted:
            self._cmp_ctnt.sort()
            self._cmp_ctnt_sorted = True
        pos = int(len(self._buffer) * rate)
        if pos == len(self._buffer):
            pos = len(self._buffer) - 1
        return self._cmp_ctnt[pos]


class StreamExampleJoiner(ExampleJoiner):
    def __init__(self, example_joiner_options, raw_data_options,
                 data_block_builder_options, kvstore, data_source,
                 partition_id):
        super(StreamExampleJoiner, self).__init__(example_joiner_options,
                                                  raw_data_options,
                                                  data_block_builder_options,
                                                  kvstore, data_source,
                                                  partition_id)
        self._min_window_size = example_joiner_options.min_matching_window
        self._max_window_size = example_joiner_options.max_matching_window
        self._leader_join_window = _JoinWindow(0.05, 0.99)
        self._follower_join_window = _JoinWindow(0.05, 0.90)
        self._joined_cache = {}
        self._leader_unjoined_example_ids = []
        self._follower_example_cache = {}
        self._fill_leader_enough = False

        self._enable_negative_example_generator = \
                example_joiner_options.enable_negative_example_generator
        if self._enable_negative_example_generator:
            sf = example_joiner_options.negative_sampling_rate
            fe = example_joiner_options.negative_sampling_filter_expr
            self._negative_example_generator = NegativeExampleGenerator(sf, fe)
        self._reset_joiner_state(True)


    @classmethod
    def name(cls):
        return 'STREAM_JOINER'

    def _inner_joiner(self, state_stale):
        if self.is_join_finished():
            return
        sync_example_id_finished, raw_data_finished = \
                self._prepare_join(state_stale)
        logging.info("streaming joiner: sync_example_id_finished: %s,"
                     "raw_data_finished: %s", sync_example_id_finished,
                     raw_data_finished)
        join_data_finished = False
        while self._fill_leader_join_window(sync_example_id_finished):
            leader_exhausted = sync_example_id_finished and \
                    self._leader_join_window.size() <= \
                    self._min_window_size / 2
            follower_exhausted = False
            delay_dump = True

            logging.info("before leader window size %d, follwer %d, "
                           "follower cache %d, leader unjoined example %d",
                           self._leader_join_window.size(),
                           self._follower_join_window.size(),
                          len(self._follower_example_cache),
                          len(self._leader_unjoined_example_ids))
            while delay_dump and \
                    self._fill_follower_join_window(raw_data_finished):
                follower_exhausted = raw_data_finished and \
                        self._follower_join_window.size() <= \
                        self._min_window_size / 2
                delay_dump = self._need_delay_dump(raw_data_finished)
                if delay_dump:
                    self._update_join_cache()
                else:
                    for meta in self._dump_joined_items():
                        yield meta
                self._evit_stale_follower_cache()
            if not delay_dump:
                self._reset_joiner_state(False)
            if leader_exhausted:
                join_data_finished = not delay_dump
            elif follower_exhausted:
                join_data_finished = True
            logging.info("delay_dump %s, join_data_finished %s, "
                           "leader_exhausted %s, follower_exhausted %s",
                           delay_dump, join_data_finished, leader_exhausted,
                           follower_exhausted)
            logging.info("leader window size %d, follwer %d, "
                           "follower cache %d, leader unjoined example %d",
                           self._leader_join_window.size(),
                           self._follower_join_window.size(),
                          len(self._follower_example_cache),
                          len(self._leader_unjoined_example_ids))
            if delay_dump or join_data_finished:
                break
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
        logging.info("delay dump leader %s, follower %s",
                     leader_qt, follower_qt)
        if leader_qt is not None and follower_qt is not None and \
                not follower_qt < leader_qt:
            return False
        return True

    def _update_join_cache(self):
        start_tm = time.time()
        new_unjoined_example_ids = []
        for example_id in self._leader_unjoined_example_ids:
            if example_id in self._follower_example_cache:
                self._joined_cache[example_id] = \
                        self._follower_example_cache[example_id]
            else:
                new_unjoined_example_ids.append(example_id)
        self._leader_unjoined_example_ids = new_unjoined_example_ids
        metrics.emit_timer(name='stream_joiner_update_join_cache',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)

    def _dump_joined_items(self):
        start_tm = time.time()
        self._neg_samples = {}
        for (leader_idx, leader_item) in self._leader_join_window:
            eid = leader_item.example_id
            if (eid not in self._follower_example_cache
               and eid not in self._joined_cache):
                if self._enable_negative_example_generator:
                    self._negative_example_generator.update(
                        {leader_idx:leader_item})
                continue
            if eid not in self._joined_cache:
                self._joined_cache[eid] = self._follower_example_cache[eid]
            follower_example = self._joined_cache[eid]
            if self._enable_negative_example_generator:
                for example in self._negative_example_generator.generate(
                    follower_example[1], leader_idx
                ):
                    builder = self._get_data_block_builder(True)
                    assert builder is not None, "data block builder must not " \
                                                "be None before dumping"
                    builder.append_item(example[0], example[1], example[2],
                                        joined=0)
                    self._optional_stats.update_stats(example[0], kind='fake')
                    if builder.check_data_block_full():
                        yield self._finish_data_block()
            prev_leader_idx = leader_idx
            builder = self._get_data_block_builder(True)
            assert builder is not None, "data block builder must not be "\
                                        "None before dumping"
            follower_idx, item = self._joined_cache[eid]
            builder.append_item(item, leader_idx, follower_idx,
                                joined=1)
            self._optional_stats.update_stats(item, kind='joined')
            if builder.check_data_block_full():
                yield self._finish_data_block()
        metrics.emit_timer(name='stream_joiner_dump_joined_items',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)

    def _reset_joiner_state(self, state_stale):
        self._leader_join_window.reset([], state_stale)
        self._fill_leader_enough = False
        self._joined_cache = {}
        self._leader_unjoined_example_ids = []
        if state_stale:
            self._follower_join_window.reset([], True)
            self._follower_example_cache = {}

    def _fill_leader_join_window(self, sync_example_id_finished):
        if not self._fill_leader_enough:
            start_tm = time.time()
            start_pos = self._leader_join_window.size()
            if not self._fill_join_windows(self._leader_visitor,
                                           self._leader_join_window,
                                           None):
                self._fill_leader_enough = sync_example_id_finished
            else:
                self._fill_leader_enough = True
            if self._fill_leader_enough:
                self._leader_unjoined_example_ids = \
                    [item.example_id for _, item in self._leader_join_window]
            end_pos = self._leader_join_window.size()
            eids = [(self._leader_join_window[idx][0],
                     self._leader_join_window[idx][1].example_id)
                    for idx in range(start_pos, end_pos)]
            self._joiner_stats.fill_leader_example_ids(eids)
            metrics.emit_timer(name='stream_joiner_fill_leader_join_window',
                               value=int(time.time()-start_tm),
                               tags=self._metrics_tags)
        return self._fill_leader_enough

    def _fill_follower_join_window(self, raw_data_finished):
        start_tm = time.time()
        start_pos = self._follower_join_window.size()
        follower_enough = self._fill_join_windows(self._follower_visitor,
                                                  self._follower_join_window,
                                                  self._follower_example_cache)
        end_pos = self._follower_join_window.size()
        eids = [(self._follower_join_window[idx][0],
                 self._follower_join_window[idx][1].example_id)
                for idx in range(start_pos, end_pos)]
        self._joiner_stats.fill_follower_example_ids(eids)
        metrics.emit_timer(name='stream_joiner_fill_leader_join_window',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)
        return follower_enough or raw_data_finished

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
        outdated = self._leader_join_window.committed_pt() is None \
                   or _CmpCtnt(item) < self._leader_join_window.committed_pt()
        if outdated and item.example_id not in self._joined_cache:
            self._optional_stats.update_stats(item, kind='unjoined')
        return outdated or item.example_id in self._joined_cache

    def _evict_if_force(self, item):
        outdated = self._leader_join_window.qt() is None or \
                _CmpCtnt(item) < self._leader_join_window.qt()
        if outdated:
            self._optional_stats.update_stats(item, kind='unjoined')
        return outdated

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
        start_tm = time.time()
        tmp_sz = self._follower_join_window.size()
        reserved_items = self._evict_impl(self._follower_join_window,
                                          self._evict_if_useless)
        logging.info("evict_if_useless %d to %d", tmp_sz, len(reserved_items))
        if len(reserved_items) < self._max_window_size:
            self._follower_join_window.reset(reserved_items, False)
            return
        tmp_sz = len(reserved_items)
        reserved_items = self._evict_impl(reserved_items,
                                          self._evict_if_force)
        logging.info("evict_if_force %d to %d", tmp_sz, len(reserved_items))
        self._follower_join_window.reset(reserved_items, False)
        metrics.emit_timer(name='stream_joiner_evit_stale_follower_cache',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)

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
