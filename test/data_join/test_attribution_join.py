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

import unittest
import random
import numpy as np
import time
import logging
import sys

from fedlearner.data_join.common import interval_to_timestamp
from fedlearner.data_join.joiner_impl import attribution_joiner as aj
from fedlearner.data_join.raw_data_iter_impl.csv_dict_iter import CsvItem

class _Item(object):
    def __init__(self, eid, et, idx):
        self.example_id = eid
        self.event_time = et
        self.index = idx

    @classmethod
    def make(cls, example_id, event_time, raw_id, fname=None, fvalue=None):
        assert fname and fvalue, "Invalid fname"
        assert fname[0] == "label" and fvalue[0] == 0, "Invalid fvalue"
        return cls(example_id, event_time, 0)

class TestAttributionJoiner(unittest.TestCase):
    def setUp(self):
        pass

    #@unittest.skip("21")
    def test_sliding_window_append(self):
        sliding_win = aj._SlidingWindow(0, 100000000)
        idx = 0
        skips = 0
        size, steps, forward, dt = 100, 20, 10, 1
        for it in [size for i in range(steps)]:
            forward_step = random.randint(1, forward)
            if sliding_win.forward(forward_step):
                skips += forward_step
            for i in range(it):
                sliding_win.append(idx, _Item(idx, idx-dt, idx))
                self.assertEqual(idx, sliding_win[idx - skips][0])
                idx += 1
        self.assertEqual(skips + sliding_win.size(), idx)
        return sliding_win, skips


    def make_sliding_window(self, size, steps, forward, dt, repeated=False):
        st = time.time()
        sliding_win = aj._SlidingWindow(0, 100000000)
        idx = 0
        skips = 0
        repeated_ev  = []
        for it in [size for i in range(steps)]:
            forward_step = forward #random.randint(1, forward)
            luckydog= []
            if sliding_win.forward(forward_step):
                skips += forward_step
            for i in range(it):
                ## disorder event
                if i % 7 == 0:
                    luckydog.append((idx, _Item(idx, idx-dt, idx)))
                else:
                    sliding_win.append(idx, _Item(idx, idx-dt, idx))
                    self.assertEqual(idx, sliding_win[idx - skips - len(luckydog)][0])
                idx += 1
            for ld in luckydog:
                sliding_win.append(ld[0], ld[1])
                if repeated:
                    repeated_ev.append((ld[0], ld[1]))

        dur = time.time() - st
        print("window mem usage %dM" % (sys.getsizeof(sliding_win._ring_buffer) / 1024 / 1024))
        print("time costs: %d(s), append num %d, skips %d, window_size=%d, alloc_size=%d" %\
              (dur, idx, skips, sliding_win.size(), sliding_win._alloc_size))
        self.assertEqual(skips + sliding_win.size(), idx)

        for (k, v) in repeated_ev:
            sliding_win.append(k, v)
        return sliding_win, skips, len(repeated_ev)

    #@unittest.skip("121")
    def test_sliding_window_accumulator(self):
        watermark = 100000000
        follower_start_index = 0
        conv_size, conv_steps = 1000, 1000
        attri = aj._Attributor(watermark)
        acc = aj._Accumulator(attri)
        conv_window, conv_skips, _ = self.make_sliding_window(conv_size, conv_steps, 10, 1)
        show_window, show_skips, _ = self.make_sliding_window(conv_size, conv_steps, 1, 2)
        res, _ = acc.join(conv_window, show_window)
        self.assertEqual(conv_size * conv_steps - conv_skips, len(res))


    def test_sliding_window_accumulator_with_repeated_conversion(self):
        watermark = 100000000
        follower_start_index = 0
        conv_size, conv_steps = 1000, 1
        attri = aj._Attributor(watermark)
        acc = aj._Accumulator(attri)
        conv_window, conv_skips, repeated = self.make_sliding_window(conv_size, conv_steps, 10, 1, True)
        show_window, show_skips, _ = self.make_sliding_window(conv_size, conv_steps, 1, 2)
        res, _ = acc.join(conv_window, show_window)
        self.assertEqual(conv_size * conv_steps - conv_skips + repeated, len(res))

    def test_interval_to_timestamp(self):
        test_in = ["1000s", "1n", "10D", "1Y2M1d3h", "1d1y", "1s1S", "111111s", "1234", "0y1n1"]
        test_out = [1000, 60, 864000, 36385200, None, None, 111111, 1234, 61]
        test_out_ = list(map(interval_to_timestamp, test_in))
        self.assertEqual(test_out, test_out_)

    def test_negative_example_generator(self):
        gen = aj.NegativeExampleGenerator()
        index_list = list(range(128))
        for i in index_list:
            gen.update({i: _Item("example_id_%d"%i, i, i)})
        item_tpl = _Item("example_id", 100, 0)

        for item in gen.generate(item_tpl, 1, 128):
            pass

    def tearDown(self):
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
