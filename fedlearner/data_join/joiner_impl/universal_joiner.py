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
import traceback

from fedlearner.common import metrics

import fedlearner.data_join.common as common
from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner
from fedlearner.data_join.negative_example_generator \
        import NegativeExampleGenerator

from fedlearner.data_join.join_expr import expression as expr
from fedlearner.data_join.key_mapper import create_key_mapper

def make_index_by_attr(keys, item, key_idx=None):
    """ Make multiple index from the keys by best-effort
        Args:
            keys: i.e. [[cid, req_id]]
            item: derived class from RawDataIter.Item
            key_idx: output indeies of the key in keys that indexed
                successfully
        Returns:
            index array
    """
    key_str_arr = []
    for idx, key in enumerate(keys):
        key_arr = key
        if isinstance(key, str):
            key_arr = [key]
        if all([hasattr(item, att) for att in key_arr]):
            if key_idx is not None:
                key_idx.append(idx)
            key_str_arr.append("_".join(
                ["%s:%s"%(name, common.convert_to_str(getattr(item, name))) \
                 for name in key_arr]))
    return key_str_arr


class _JoinerImpl(object):
    def __init__(self, exp):
        self._expr = exp

    def join(self, follower_window, leader_window):
        """
        Assume leader stream is exponentially larger than follower stream,
        we cache the all the events from now back to watermark. example id
        maybe duplicated in follower stream
        Return:
            show_matches: an array with tuples(follower, leader), in same order
                with leader event
        """
        leader_matches = []
        leader_mismatches = {}
        # keys example: [(req_id, cid), click_id]
        keys = self._expr.keys()
        follower_dict = follower_window.as_dict(keys)
        idx = 0
        while idx < leader_window.size():
            elem = leader_window[idx]
            #1. find the first matching key
            key_idx = []
            if not leader_window.key_map_fn(elem):
                idx += 1
                continue
            leader = elem.item
            key_str_arr = make_index_by_attr(
                keys, leader, key_idx)
            found = False
            for ki, k in enumerate(key_str_arr):
                if k not in follower_dict:
                    continue
                cd = follower_dict[k]
                key_idx = key_idx[ki]
                for i in reversed(range(len(cd))):
                    #A leader can match multiple conversion event, add
                    # all the matched conversion-leader pair to result
                    follower = follower_window[cd[i]].item
                    #2. select all the matching items from the specific key
                    # in follower side.
                    if self._expr.run_func(key_idx)(leader, follower):
                        leader_matches.append((cd[i], idx))
                found = True
                break
            if not found:
                leader_mismatches[leader_window[idx].index] = leader
            idx += 1
        return leader_matches, leader_mismatches

class _Trigger(object):
    """Update watermark. We assume the item contains field event_time"""
    def __init__(self, max_watermark_delay):
        self._max_watermark_delay = max_watermark_delay
        self._watermark = 0

    def watermark(self):
        return self._watermark

    def shrink(self, window):
        ed = window[window.size() - 1]
        idx = 0
        while idx < window.size() and common.time_diff(                       \
                    ed.item.event_time,                                       \
                    window[idx].item.event_time)                              \
                > self._max_watermark_delay:
            self._watermark = window[idx].item.event_time
            idx += 1
        return idx

    def trigger(self, follower_window, leader_window):
        follower_stride, leader_stride = 0, 0
        step, sid = 1, 0
        leader_win_size = leader_window.size() - 1
        follower_win_size = follower_window.size() - 1
        while leader_stride <= leader_win_size and                             \
                sid <= leader_win_size and                                     \
                follower_win_size >= 0 and                                     \
                common.time_diff(                                              \
                    follower_window[follower_win_size].item.event_time,        \
                    leader_window[sid].item.event_time) >                      \
                self._max_watermark_delay:
            leader_stride += step
            sid += 1

        cid = 0
        while follower_stride <= follower_win_size and                         \
                leader_win_size >= 0 and                                       \
                0 <= cid <= follower_win_size and                              \
                common.time_diff(                                              \
                  leader_window[leader_win_size].item.event_time,              \
                  follower_window[cid].item.event_time) >                      \
                self._max_watermark_delay:
            #FIXME current et is not always the watermark
            self._watermark = max(follower_window[cid].item.event_time,        \
                                  self._watermark)
            follower_stride += step
            cid += 1

        logging.info("Watermark forward to %d by (follower: %d, leader: %d)",  \
                    self._watermark, follower_stride, leader_stride)
        return (follower_stride, leader_stride)

class _SlidingWindow(object):
    """Sliding and unfixed-size window"""
    class Element(object):
        """index is the index of item in rawdata"""
        def __init__(self, idx, item):
            self.index = idx
            self.item = item
            self.is_mapped = False
    def __init__(self, init_window_size, max_window_size, mapper):
        self._init_window_size = max(init_window_size, 1)
        self._max_window_size = max_window_size
        self._ring_buffer = list(range(self._init_window_size))
        self._start = 0
        self._end = 0
        self._alloc_size = self._init_window_size
        self._size = 0
        self._debug_extend_cnt = 0
        self._key_map_fn = mapper

    def key_map_fn(self, elem):
        assert isinstance(elem, _SlidingWindow.Element), \
                "elem instance %s is not Element"%elem
        if elem.is_mapped:
            return True
        try:
            mapped_item = self._key_map_fn(elem.item)
            for (k, v) in mapped_item.items():
                setattr(elem.item, k, v)
            elem.is_mapped = True
            return True
        except Exception as e: #pylint: disable=broad-except
            logging.warning("key mapping failed for %s", elem.item.__dict__)
            traceback.print_exc()
            return False

    def __str__(self):
        return "start: %d, end: %d, size: %d, alloc_size: %d, buffer: %s"% \
                (self._start, self._end, self._size, self._alloc_size,     \
                 self._ring_buffer[self.start():                           \
                                   (self.start()+20)%self._alloc_size])
    def as_dict(self, keys):
        """
            multi-key index construction:
                buf:    key -> [idx]
                window: idx -> item
        """
        buf = {}
        idx = 0
        while idx < self.size():
            elem = self.__getitem__(idx)
            if not self.key_map_fn(elem):
                idx += 1
                continue
            for key in make_index_by_attr(keys, elem.item):
                if key not in buf:
                    buf[key] = [idx]
                else:
                    buf[key].append(idx)
            idx += 1
        return buf

    def start(self):
        return self._start

    def end(self):
        return self._end

    def size(self):
        return self._size

    def is_full(self):
        return self._size == self._alloc_size

    def et_span(self):
        if self._size == 0:
            return 0
        st = self._ring_buffer[self._start].item.event_time
        ed = self._ring_buffer[self._index(self._size - 1)].item.event_time
        return common.time_diff(ed, st)

    def reserved_size(self):
        return self._max_window_size - self._size

    def append(self, index, item):
        # item: raw_data_iter.RawDataIter.Item
        if self._size >= self._alloc_size:
            self.extend()
        assert self._size < self._alloc_size, "Window extend failed"
        self._ring_buffer[self._end] = self.Element(index, item)
        self._end = (self._end + 1) % self._alloc_size
        self._size += 1

    def _defragment(self, new_buf):
        """
        defragment the ring buffer, and copy it to new_buf
        """
        if self._end == 0:
            new_buf[0:self._size] = \
                    self._ring_buffer[self._start:self._alloc_size]
        elif self._start < self._end:
            new_buf[0:self._size] = \
                    self._ring_buffer[self._start:self._end]
        else:
            part_1 = self._alloc_size - self._start
            new_buf[0:part_1] = self._ring_buffer[self._start:self._alloc_size]
            part_2 = self._end
            if part_2 >= 0:
                new_buf[part_1:part_1+part_2] = self._ring_buffer[0:part_2]

    def extend(self):
        logging.info("%s extend begin, begin=%d, end=%d, size=%d, "
                     "alloc_size=%d, len(ring_buffer)=%d, extend_cnt=%d",     \
                     self.__class__.__name__, self._start, self._end,         \
                     self._size, self._alloc_size, len(self._ring_buffer),    \
                     self._debug_extend_cnt)
        assert self._alloc_size < self._max_window_size,                      \
                "Can't extend ring buffer due to max_window_size limit"
        new_alloc_size = min(self._alloc_size * 2, self._max_window_size)
        new_buf = list(range(new_alloc_size))
        self._defragment(new_buf)
        self._start = 0
        self._end = self._size
        self._alloc_size = new_alloc_size
        self._ring_buffer = new_buf
        self._debug_extend_cnt += 1
        logging.info("%s extend end, begin=%d, end=%d, size=%d, "
                     "alloc_size=%d, len(ring_buffer)=%d, extend_cnt=%d",     \
                     self.__class__.__name__, self._start, self._end,         \
                     self._size, self._alloc_size, len(self._ring_buffer),    \
                     self._debug_extend_cnt)

    def reset(self, new_buffer, state_stale):
        self._start = 0
        self._end = len(new_buffer)
        self._size = len(new_buffer)
        self._ring_buffer[0:self._size-1] = new_buffer[0:self._size-1]

    def _index(self, index):
        return (self._start + index) % self._alloc_size

    def __getitem__(self, index):
        if index > self._alloc_size:
            logging.warning("index %d out of range %d, be truncated",         \
                         index, self._alloc_size)
        return self._ring_buffer[self._index(index)]

    def forward(self, step):
        if self._size < step:
            return False
        self._start = self._index(step)
        self._size -= step
        return True

class UniversalJoiner(ExampleJoiner):
    def __init__(self, example_joiner_options, raw_data_options,
                 data_block_builder_options, kvstore, data_source,
                 partition_id):
        super(UniversalJoiner, self).__init__(example_joiner_options,
                                                  raw_data_options,
                                                  data_block_builder_options,
                                                  kvstore, data_source,
                                                  partition_id)
        self._min_window_size = example_joiner_options.min_matching_window
        self._max_window_size = example_joiner_options.max_matching_window

        self._max_watermark_delay = \
                example_joiner_options.max_conversion_delay

        self._key_mapper = create_key_mapper(
            example_joiner_options.join_key_mapper)
        self._leader_join_window = _SlidingWindow(
            self._min_window_size, self._max_window_size,
            self._key_mapper.leader_mapping)
        self._follower_join_window = _SlidingWindow(
            self._min_window_size, self._max_window_size,
            self._key_mapper.follower_mapping)
        self._leader_restart_index = -1
        self._sorted_buf_by_leader_index = []
        self._dedup_by_follower_index = {}
        self._trigger = _Trigger(self._max_watermark_delay)
        self._expr = expr.Expr(example_joiner_options.join_expr)
        self._joiner = _JoinerImpl(self._expr)

        self._enable_negative_example_generator = \
                example_joiner_options.enable_negative_example_generator
        if self._enable_negative_example_generator:
            sf = example_joiner_options.negative_sampling_rate
            fe = example_joiner_options.exampling_filter_expr
            self._negative_example_generator = NegativeExampleGenerator(sf, fe)

    @classmethod
    def name(cls):
        return 'UNIVERSAL_JOINER'

    def _inner_joiner(self, state_stale):
        if self.is_join_finished():
            return
        sync_example_id_finished, raw_data_finished = \
                self._prepare_join(state_stale)
        join_data_finished = False

        # leader: no enough elems filled but syncing is going on, will break
        #  and wait.
        while self._fill_leader_join_window(sync_example_id_finished):
            leader_exhausted = sync_example_id_finished and                    \
                    self._leader_join_window.et_span() <=                      \
                    self._max_watermark_delay
            # follower:  no syncing cost, so it always can be filled enough
            #  unless buffer overflow
            follower_enough = self._fill_follower_join_window(raw_data_finished)
            follower_exhausted = raw_data_finished and \
                    self._follower_join_window.size() <= \
                    self._min_window_size / 2

            logging.info("Fill: leader_exhausted=%s, follower_enough=%s"       \
                         " sync_example_id_finished=%s, raw_data_finished=%s"  \
                         " leader_win_size=%d, follower_win_size=%d",          \
                         leader_exhausted, follower_enough,                    \
                         sync_example_id_finished,                             \
                        raw_data_finished, self._leader_join_window.size(),    \
                        self._follower_join_window.size())

            watermark = self._trigger.watermark()
            #1. find all the matched pairs in current window
            raw_pairs, mismatches = self._joiner.join(
                self._follower_join_window, self._leader_join_window)
            if self._enable_negative_example_generator:
                self._negative_example_generator.update(mismatches)
            #2. cache the pairs, evict the leader events which are out of
            # watermark
            pairs = self._sort_and_evict_leader_buf(raw_pairs, watermark)
            #3. push the result into builder
            if len(pairs) > 0:
                for meta in self._dump_joined_items(pairs):
                    yield meta
                self._leader_restart_index = pairs[len(pairs) - 1][1]
                self._follower_restart_index = pairs[len(pairs) - 1][2]
            logging.info("Restart index of leader %d, follwer %d, pair_buf=%d,"\
                         " raw_pairs=%d, pairs=%d", self._leader_restart_index,\
                         self._follower_restart_index,
                         len(self._sorted_buf_by_leader_index), len(raw_pairs),
                         len(pairs))

            #4. update the watermark
            stride = self._trigger.trigger(self._follower_join_window,  \
                                           self._leader_join_window)
            self._follower_join_window.forward(stride[0])
            self._leader_join_window.forward(stride[1])

            if leader_exhausted or follower_exhausted:
                join_data_finished = True
                break

            force_stride = self._trigger.shrink(self._follower_join_window)
            self._follower_join_window.forward(force_stride)
            force_stride = self._trigger.shrink(self._leader_join_window)
            self._leader_join_window.forward(force_stride)

        if self._get_data_block_builder(False) is not None and \
                (self._need_finish_data_block_since_interval() or
                    join_data_finished):
            yield self._finish_data_block()
        if join_data_finished:
            self._set_join_finished()
            logging.info("finish join example for partition %d by %s",
                            self._partition_id, self.name())

    def _latest_attri(self, index):
        lf, rt = 0, len(self._sorted_buf_by_leader_index)
        while lf < rt:
            mid = (lf + rt) // 2
            if index < self._sorted_buf_by_leader_index[mid][1]:
                rt = mid
            else:
                lf = mid + 1
        return lf

    def _sort_and_evict_leader_buf(self, raw_matches, watermark):
        """
        Push the matched pairs to order-by-leader-index list,
        and evict the pairs which are out of watermark
        """
        for (cid, sid) in raw_matches:
            #fi: follower index, fe: follower example
            assert cid < self._follower_join_window.size(), "Invalid l index"
            assert sid < self._leader_join_window.size(), "Invalid f index"

            example_with_index = self._follower_join_window[cid]
            fi, fe = example_with_index.index, example_with_index.item

            example_with_index = self._leader_join_window[sid]
            li, le = example_with_index.index, example_with_index.item
            if li <= self._leader_restart_index:
                logging.warning("Unordered event ignored, leader index should"\
                                " be greater %d > %d for follower idx %d is"  \
                                " false", li, self._leader_restart_index, fi)
                continue

            # cache the latest leader event
            updated = False
            if fi in self._dedup_by_follower_index:
                if self._dedup_by_follower_index[fi][1] > le.event_time:
                    self._dedup_by_follower_index[fi] = (li, le.event_time)
                    updated = True
            else:
                self._dedup_by_follower_index[fi] = (li, le.event_time)
                updated = True
            # sort by leader index
            if not updated:
                continue
            latest_pos = self._latest_attri(li)
            if latest_pos > 0:
                # remove the dups
                latest_item = \
                    self._sorted_buf_by_leader_index[latest_pos - 1]
                if latest_item[1] == li and latest_item[2] == fi:
                    continue
            self._sorted_buf_by_leader_index.insert(latest_pos, \
                                          (fe, li, fi))
        matches = []
        idx = 0
        for (fe, li, fi) in self._sorted_buf_by_leader_index:
            if fe.event_time <= watermark:
                assert fi in self._dedup_by_follower_index, \
                        "Invalid index[%d]"%fi
                (leader_index, _) = self._dedup_by_follower_index[fi]
                if leader_index == li:
                    matches.append((fe, li, fi))
                    del self._dedup_by_follower_index[fi]
                else:
                    logging.info("Example %s matching leader index %s is"   \
                                 " older than %d", fe.example_id, li,       \
                                 leader_index)
            else:
                # FIXME: Assume the unordered range is limited,
                #  or this will raise out-of-memory
                break
            idx += 1
        self._sorted_buf_by_leader_index \
                = self._sorted_buf_by_leader_index[idx:]
        return matches

    # useless
    def _reset_joiner_state(self, state_stale):
        self._leader_join_window.reset([], state_stale)
        if state_stale:
            self._follower_join_window.reset([], True)

    def _prepare_join(self, state_stale):
        if state_stale:
            self._reset_joiner_state(True)
        return super(UniversalJoiner, self)._prepare_join(state_stale)

    def _dump_joined_items(self, matching_list):
        start_tm = time.time()
        for item in matching_list:
            (fe, li, fi) = item
            if self._enable_negative_example_generator:
                for example in \
                    self._negative_example_generator.generate(fe, li):
                    builder = self._get_data_block_builder(True)
                    assert builder is not None, "data block builder must be "\
                                                "not None if before dummping"
                    # example:  (li, fi, item)
                    builder.append_item(example[0], example[1],
                                        example[2], None, True)
                    if builder.check_data_block_full():
                        yield self._finish_data_block()

            builder = self._get_data_block_builder(True)
            assert builder is not None, "data block builder must be "\
                                        "not None if before dummping"
            builder.append_item(fe, li, fi, None, True, joined=1)
            if builder.check_data_block_full():
                yield self._finish_data_block()
        metrics.emit_timer(name='universal_joiner_dump_joined_items',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)

    def _fill_leader_join_window(self, sync_example_id_finished):
        start_tm = time.time()
        idx = self._leader_join_window.size()
        filled_enough = self._fill_join_windows(self._leader_visitor,
                                       self._leader_join_window)
        if not filled_enough:
            filled_enough = sync_example_id_finished
        eids = []
        while idx < self._leader_join_window.size():
            eids.append((self._leader_join_window[idx].index,
                        self._leader_join_window[idx].item.example_id))
            idx += 1

        self._joiner_stats.fill_leader_example_ids(eids)
        metrics.emit_timer(name=\
                           'universal_joiner_fill_leader_join_window',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)
        return filled_enough

    def _fill_follower_join_window(self, raw_data_finished):
        start_tm = time.time()
        idx = self._follower_join_window.size()
        filled_enough = self._fill_join_windows(self._follower_visitor,
                                      self._follower_join_window)
        eids = []
        while idx < self._follower_join_window.size():
            eids.append((self._follower_join_window[idx].index,
                 self._follower_join_window[idx].item.example_id))
            idx += 1

        self._joiner_stats.fill_follower_example_ids(eids)
        metrics.emit_timer(name=\
                           'universal_joiner_fill_follower_join_window',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)
        return filled_enough or raw_data_finished

    def _fill_join_windows(self, visitor, join_window):
        size = join_window.size()
        while not visitor.finished() and not join_window.is_full():
            required_item_count = join_window.reserved_size()
            self._consume_item_until_count(
                    visitor, join_window,
                    required_item_count
                )
        # return True if new elem added or window reaches its capacity
        return join_window.size() > size or size >= self._max_window_size

    def _consume_item_until_count(self, visitor, windows,
                                  required_item_count):
        for (index, item) in visitor:
            if item.example_id == common.InvalidExampleId:
                logging.warning("ignore item indexed as %d from %s since "\
                                "invalid example id", index, visitor.name())
            elif item.event_time == common.InvalidEventTime:
                logging.warning("ignore item indexed as %d from %s since "\
                                "invalid event time", index, visitor.name())
            else:
                windows.append(index, item)
                if windows.size() >= required_item_count:
                    return
        assert visitor.finished(), "visitor shoud be finished of "\
                                   "required_item is not satisfied"
