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
from fedlearner.data_join.joiner_impl import universal_joiner as aj
from fedlearner.data_join.raw_data_iter_impl.csv_dict_iter import CsvItem
from fedlearner.data_join.key_mapper import create_key_mapper
from fedlearner.data_join.join_expr.expression import Expr

class TestSlidingWindow(unittest.TestCase):
    def setUp(self):
        self._mapper = create_key_mapper('DEFAULT')

    #@unittest.skip("21")
    def test_sliding_window_append(self):
        sliding_win = aj._SlidingWindow(0, 100000000, self._mapper.leader_mapping)
        idx = 0
        skips = 0
        size, steps, forward, dt = 100, 20, 10, 1
        for it in [size for i in range(steps)]:
            forward_step = random.randint(1, forward)
            if sliding_win.forward(forward_step):
                skips += forward_step
            for i in range(it):
                sliding_win.append(idx, CsvItem({'example_id': str(idx), 'event_time': idx-dt, 'index': idx}))
                self.assertEqual(idx, sliding_win[idx - skips].index)
                idx += 1
        self.assertEqual(skips + sliding_win.size(), idx)
        return sliding_win, skips


    def make_sliding_window(self, size, steps, forward, dt, repeated=False):
        st = time.time()
        sliding_win = aj._SlidingWindow(0, 100000000, self._mapper.leader_mapping)
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
                    luckydog.append((idx, CsvItem({'example_id': str(idx), 'event_time': idx-dt, 'index': idx})))
                else:
                    sliding_win.append(idx, CsvItem({'example_id': str(idx), 'event_time': idx-dt, 'index': idx}))
                    self.assertEqual(idx, sliding_win[idx - skips - len(luckydog)].index)
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
        acc = aj._JoinerImpl(Expr("(example_id, lt(event_time))"))
        conv_window, conv_skips, _ = self.make_sliding_window(conv_size, conv_steps, 10, 1)
        show_window, show_skips, _ = self.make_sliding_window(conv_size, conv_steps, 1, 2)
        res, _ = acc.join(conv_window, show_window)
        self.assertEqual(conv_size * conv_steps - conv_skips, len(res))


    def test_sliding_window_accumulator_with_repeated_conversion(self):
        watermark = 100000000
        follower_start_index = 0
        conv_size, conv_steps = 1000, 1
        acc = aj._JoinerImpl(Expr("(example_id, lt(event_time))"))
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
        gen = aj.NegativeExampleGenerator(1.0, 'et(index, 0)')
        index_list = list(range(128))
        for i in index_list:
            gen.update({i: CsvItem({'example_id': "example_id_%d"%i, 'event_time': i, 'index': i})})
        item_tpl = CsvItem({'example_id': "example_id", 'event_time': 100, 'index': 0})

        cnt = 0
        for item in gen.generate(item_tpl, 128):
            cnt += 1
        self.assertEqual(cnt, 1)

    def test_ps(self):
        ps = aj.PrioritySet()
        ps.put(aj._IndexedPair(None, 1, 2))
        ps.put(aj._IndexedPair(None, 1, 2))
        assert ps.size() == 1
        ps.put(aj._IndexedPair(None, 1, 3))
        ps.put(aj._IndexedPair(None, 2, 3))
        item = ps.get()
        assert item.li == 1 and item.fi == 2
        item = ps.get()
        assert item.li == 1 and item.fi == 3

        assert ps.size() == 1

    def tearDown(self):
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
