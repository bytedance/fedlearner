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

from fedlearner.common import metrics

import fedlearner.data_join.common as common
from fedlearner.data_join.joiner_impl.example_joiner import ExampleJoiner

class NegativeExampleGenerator(object):
    def __init__(self):
        self._buf = {}

    def update(self, mismatches):
        self._buf.update(mismatches)

    def generate(self, fe, prev_leader_idx, leader_idx):
        for idx in range(prev_leader_idx, leader_idx):
            if idx not in self._buf:
                continue
            example_id = self._buf[idx].example_id
            event_time = self._buf[idx].event_time
            example = type(fe).make(example_id, event_time,
                                       example_id, ["label"], [0])
            yield (example, idx, 0)
            del self._buf[idx]

        del_keys = [k for k in self._buf if k < prev_leader_idx]
        for k in del_keys:
            del self._buf[k]

class _Attributor(object):
    """
    How we attribute the covertion event to the show event
    """
    def __init__(self, max_conversion_delay):
        self._max_conversion_delay = max_conversion_delay

    def match(self, conv, show):
        assert hasattr(conv, "example_id"), "invalid item, no example id"
        assert hasattr(show, "example_id"), "invalid item, no example id"
        return conv.example_id == show.example_id and \
                conv.event_time > show.event_time and \
                conv.event_time <= show.event_time +  \
                self._max_conversion_delay

class _Accumulator(object):
    def __init__(self, attributor):
        self._attributor = attributor

    def join(self, conv_window, show_window):
        """
        Assume show stream is exponentially larger than convert stream,
        we cache the all the events from now back to watermark. example id
        maybe duplicated in convert stream
        Return:
            show_matches: an array with tuples(convet, show), in same order
                with show event
        """
        show_matches = []
        show_mismatches = {}
        conv_dict = conv_window.as_dict()
        idx = 0
        while idx < show_window.size():
            show = show_window[idx][1]
            if show.example_id in conv_dict:
                cd = conv_dict[show.example_id]
                for i in reversed(range(len(cd))):
                    #A show can match multiple conversion event, add
                    # all the matched conversion-show pair to result
                    conv = conv_window[cd[i]][1]
                    if self._attributor.match(conv, show):
                        show_matches.append((cd[i], idx))
            else:
                show_mismatches[show_window[idx][0]] = show
            idx += 1
        return show_matches, show_mismatches

class _Trigger(object):
    """
    Decide how to move forward the watermark
    """
    def __init__(self, max_conversion_delay):
        self._max_conversion_delay = max_conversion_delay
        self._watermark = 0

    def watermark(self):
        return self._watermark

    def shrink(self, conv_window):
        ed = conv_window[conv_window.size() - 1]
        idx = 0
        while idx < conv_window.size() and ed[1].event_time > \
              conv_window[idx][1].event_time + self._max_conversion_delay:
            self._watermark = conv_window[idx][1].event_time
            idx += 1
        return idx

    def trigger(self, conv_window, show_window):
        conv_stride, show_stride = 0, 0
        ## step can be increased to accelerate this
        step = 1
        show_win_size = show_window.size() - 1
        conv_win_size = conv_window.size() - 1
        sid = 0
        while show_stride <= show_win_size and sid <= show_win_size    \
                and conv_win_size >= 0                                 \
                and conv_window[0][1].event_time >                     \
                show_window[sid][1].event_time +                       \
                    self._max_conversion_delay:
            show_stride += step
            sid += 1

        cid = 0
        while conv_stride <= conv_win_size and show_win_size >= 0 and  \
              0 <= cid <= conv_win_size and                            \
              show_window[show_win_size][1].event_time >               \
              conv_window[cid][1].event_time +                         \
                    self._max_conversion_delay:
            #FIXME current et is not always the watermark
            self._watermark = max(conv_window[cid][1].event_time,      \
                                  self._watermark)
            conv_stride += step
            cid += 1

        logging.info("Watermark triggered forward to %d by "           \
                     "(conv: %d, show: %d)",                           \
                    self._watermark, conv_stride, show_stride)
        return (conv_stride, show_stride)

class _SlidingWindow(object):
    """
    Sliding and unfixed-size window
    """
    def __init__(self, init_window_size, max_window_size):
        self._init_window_size = max(init_window_size, 1)
        self._max_window_size = max_window_size
        self._ring_buffer = list(range(self._init_window_size))
        self._start = 0
        self._end = 0
        self._alloc_size = self._init_window_size
        self._size = 0
        self._debug_extend_cnt = 0

    def __str__(self):
        return "start: %d, end: %d, size: %d, alloc_size: "             \
                "%d, ring_buffer: %s" %                                 \
                (self._start, self._end, self._size, self._alloc_size,  \
                 self._ring_buffer[self.start():                        \
                                   (self.start()+20)%self._alloc_size])
    def as_dict(self):
        buf = {}
        idx = 0
        ## assume that the duplicated example is few
        while idx < self.size():
            item = self.__getitem__(idx)[1]
            if item.example_id not in buf:
                buf[item.example_id] = [idx]
            else:
                buf[item.example_id].append(idx)
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
        st = self._ring_buffer[self._start][1].event_time
        ed = self._ring_buffer[self._index(self._size - 1)][1].event_time
        return ed - st

    def reserved_size(self):
        return self._max_window_size - self._size

    def append(self, index, item):
        if self._size >= self._alloc_size:
            self.extend()
        assert self._size < self._alloc_size, "Window extend failed"
        self._ring_buffer[self._end] = (index, item)
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
                     "alloc_size=%d, len(ring_buffer)=%d, extend_cnt=%d",  \
                     self.__class__.__name__, self._start, self._end,      \
                     self._size, self._alloc_size, len(self._ring_buffer), \
                     self._debug_extend_cnt)
        assert self._alloc_size < self._max_window_size,                   \
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
                     "alloc_size=%d, len(ring_buffer)=%d, extend_cnt=%d",  \
                     self.__class__.__name__, self._start, self._end,      \
                     self._size, self._alloc_size, len(self._ring_buffer), \
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
            logging.warning("index %d out of range %d, be truncated", \
                         index, self._alloc_size)
        return self._ring_buffer[self._index(index)]

    def forward(self, step):
        if self._size < step:
            return False
        self._start = self._index(step)
        self._size -= step
        return True

class AttributionJoiner(ExampleJoiner):
    def __init__(self, example_joiner_options, raw_data_options,
                 data_block_builder_options, kvstore, data_source,
                 partition_id):
        super(AttributionJoiner, self).__init__(example_joiner_options,
                                                  raw_data_options,
                                                  data_block_builder_options,
                                                  kvstore, data_source,
                                                  partition_id)
        self._min_window_size = example_joiner_options.min_matching_window
        # max_window_size must be lesser than max_conversion_delay
        self._max_window_size = example_joiner_options.max_matching_window
        self._max_conversion_delay = \
                example_joiner_options.max_conversion_delay
        self._leader_join_window = _SlidingWindow(self._min_window_size,
                                                  1000000)
        self._follower_join_window = _SlidingWindow(
            self._min_window_size, self._max_window_size)
        self._leader_restart_index = -1
        self._sorted_buf_by_leader_index = []
        self._dedup_by_follower_index = {}

        self._trigger = _Trigger(self._max_conversion_delay)
        attri = _Attributor(self._max_conversion_delay)
        self._acc = _Accumulator(attri)

        self._enable_negative_example_generator = \
                example_joiner_options.enable_negative_example_generator
        if self._enable_negative_example_generator:
            self._negative_example_generator = NegativeExampleGenerator()

    @classmethod
    def name(cls):
        return 'ATTRIBUTION_JOINER'

    def _inner_joiner(self, state_stale):
        if self.is_join_finished():
            return
        sync_example_id_finished, raw_data_finished = \
                self._prepare_join(state_stale)
        join_data_finished = False

        leader_fstep = 1
        while True:
            leader_filled = self._fill_leader_join_window()
            leader_exhausted = sync_example_id_finished and \
                    self._leader_join_window.et_span() <    \
                    self._max_conversion_delay
            follower_filled = self._fill_follower_join_window()
            follower_exhausted = raw_data_finished and     \
                    self._follower_join_window.et_span() < \
                    self._max_conversion_delay
            logging.info("Fill: leader_filled=%s, leader_exhausted=%s,"\
                         " follower_filled=%s, follower_exhausted=%s,"\
                         " sync_example_id_finished=%s, raw_data_finished=%s",\
                        leader_filled, leader_exhausted, \
                        follower_filled, follower_exhausted,\
                        sync_example_id_finished, raw_data_finished)

            watermark = self._trigger.watermark()
            #1. find all the matched pairs in current window
            raw_pairs, mismatches = self._acc.join(self._follower_join_window,\
                        self._leader_join_window)
            if self._enable_negative_example_generator:
                self._negative_example_generator.update(mismatches)
            #2. cache the pairs, evict the show events which are out of
            # watermark
            pairs = self._sort_and_evict_attri_buf(raw_pairs, watermark)
            #3. push the result into builder
            if len(pairs) > 0:
                self._leader_restart_index = pairs[len(pairs) - 1][1]
                self._follower_restart_index = pairs[len(pairs) - 1][2]
                for meta in self._dump_joined_items(pairs):
                    yield meta
            logging.info("Restart index for leader %d, follwer %d",     \
                          self._leader_restart_index,                   \
                          self._follower_restart_index)

            #4. update the watermark
            stride = self._trigger.trigger(self._follower_join_window,  \
                                           self._leader_join_window)
            self._follower_join_window.forward(stride[0])
            self._leader_join_window.forward(stride[1])
            logging.info("Stat: pair_buf=%d, raw_pairs=%d, pairs=%d, "  \
                         "stride=%s",                                   \
                         len(self._sorted_buf_by_leader_index),         \
                         len(raw_pairs), len(pairs), stride)

            if not leader_filled and not sync_example_id_finished:
                logging.info("Wait for Leader syncing example id...")
                break
            if leader_exhausted:
                join_data_finished = True
                break

            if stride == (0, 0):
                if raw_data_finished:
                    self._leader_join_window.forward(leader_fstep)
                    leader_fstep = min(leader_fstep * 2,
                                       (self._leader_join_window.size()+1)//2)

                if sync_example_id_finished:
                    force_stride = \
                            self._trigger.shrink(self._follower_join_window)
                    self._follower_join_window.forward(force_stride)

            else:
                leader_fstep = 1

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

    def _sort_and_evict_attri_buf(self, raw_matches, watermark):
        """
        Push the matched pairs to order-by-leader-index list,
        and evict the pairs which are out of watermark
        """
        for (cid, sid) in raw_matches:
            #fi: follower index, fe: follower example
            assert cid < self._follower_join_window.size(), "Invalid l index"
            assert sid < self._leader_join_window.size(), "Invalid f index"
            (fi, fe) = self._follower_join_window[cid]
            (li, le) = self._leader_join_window[sid]
            assert fe.example_id == le.example_id, "Example id must be equal"
            if li <= self._leader_restart_index:
                logging.warning("Unordered event ignored, leader index should"\
                                " be greater %d > %d for follower idx %d is"  \
                                " false", li, self._leader_restart_index, fi)
                continue

            # cache the latest show event
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
                assert fi in self._dedup_by_follower_index, "Invalid f index"
                (leader_index, _) = self._dedup_by_follower_index[fi]
                if leader_index == li:
                    matches.append((fe, li, fi))
                    del self._dedup_by_follower_index[fi]
                else:
                    logging.info("Example %s matching leader index %s is"\
                                 " older than %d", fe.example_id, li,    \
                                 leader_index)
            else:
                # FIXME: Assume the unordered range is limited,
                #  or this will bring an out-of-memory crash
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
        return super(AttributionJoiner, self)._prepare_join(state_stale)

    def _dump_joined_items(self, matching_list):
        start_tm = time.time()
        prev_leader_idx = self._leader_restart_index + 1
        for item in matching_list:
            builder = self._get_data_block_builder(True)
            assert builder is not None, "data block builder must be "\
                                        "not None if before dummping"
            (fe, li, fi) = item
            if self._enable_negative_example_generator:
                for example in \
                    self._negative_example_generator.generate(
                        fe, prev_leader_idx, li):
                    # fi is useless here
                    builder.append_item(example[0], example[1],
                                        example[2], None, True)
                    if builder.check_data_block_full():
                        yield self._finish_data_block()
            builder.append_item(fe, li, fi, None, True)
            if builder.check_data_block_full():
                yield self._finish_data_block()
            prev_leader_idx = li
        metrics.emit_timer(name='attribution_joiner_dump_joined_items',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)

    def _fill_leader_join_window(self):
        start_tm = time.time()
        idx = self._leader_join_window.size()
        filled_new_example = self._fill_join_windows(self._leader_visitor,
                                       self._leader_join_window)
        eids = []
        while idx < self._leader_join_window.size():
            eids.append((self._leader_join_window[idx][0],
                        self._leader_join_window[idx][1].example_id))
            idx += 1

        self._joiner_stats.fill_leader_example_ids(eids)
        metrics.emit_timer(name=\
                           'attribution_joiner_fill_leader_join_window',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)
        return filled_new_example

    def _fill_follower_join_window(self):
        start_tm = time.time()
        idx = self._follower_join_window.size()
        filled_new_example = self._fill_join_windows(self._follower_visitor,
                                      self._follower_join_window)
        eids = []
        while idx < self._follower_join_window.size():
            eids.append((self._follower_join_window[idx][0],
                 self._follower_join_window[idx][1].example_id))
            idx += 1

        self._joiner_stats.fill_follower_example_ids(eids)
        metrics.emit_timer(name=\
                           'attribution_joiner_fill_follower_join_window',
                           value=int(time.time()-start_tm),
                           tags=self._metrics_tags)
        return filled_new_example

    def _fill_join_windows(self, visitor, join_window):
        size = join_window.size()
        while not visitor.finished() and not join_window.is_full():
            required_item_count = join_window.reserved_size()
            self._consume_item_until_count(
                    visitor, join_window,
                    required_item_count
                )
        return join_window.size() > size

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
