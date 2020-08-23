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

import uuid

from cityhash import CityHash64 # pylint: disable=no-name-in-module

class _SlideCache(object):
    def __init__(self, stats_index, stats_windows_size):
        self._slide_buffer = [0] * stats_windows_size
        self._cache = {}
        self._stats_index = stats_index
        self._stats_windows_size = stats_windows_size
        self._begin_index = 0
        self._item_cnt = 0

    def fill_hash_ids(self, stats_index, hids):
        if stats_index > self._stats_index:
            self._stats_index = stats_index
        evict_cnt = 0
        if len(hids) + self._item_cnt > self._stats_windows_size:
            evict_cnt = len(hids) + self._item_cnt - self._stats_windows_size
        evict_hids = [self._slide_buffer[self._inner_index(idx)]
                      for idx in range(evict_cnt)]
        for idx, hid in enumerate(hids):
            ridx = self._inner_index(self._item_cnt+idx)
            self._slide_buffer[ridx] = hid
            if hid not in self._cache:
                self._cache[hid] = 1
            else:
                self._cache[hid] += 1
        for hid in evict_hids:
            if hid in self._cache and self._cache[hid] > 0:
                self._cache[hid] -= 1
                if self._cache[hid] == 0:
                    self._cache.pop(hid)
        if evict_cnt > 0:
            self._item_cnt = self._stats_windows_size
        else:
            self._item_cnt += len(hids)
        self._begin_index = (self._begin_index + evict_cnt) % \
                self._stats_windows_size
        return evict_hids

    def get_stats_index(self):
        return self._stats_index

    def __iter__(self):
        for i in range(self._item_cnt):
            ri = self._inner_index(i)
            yield self._slide_buffer[ri]

    def __getitem__(self, hid):
        if hid not in self._cache:
            return 0
        return self._cache[hid]

    def _inner_index(self, index):
        return (index + self._begin_index) % self._stats_windows_size

class JoinerStats(object):
    _SampleRateReciprocal = 32
    def __init__(self, stats_cum_join_num, leader_join_index,
                 follower_join_index, max_stats_windows_size=1<<16):
        self._hash_prefix = str(uuid.uuid1())
        self._stats_cum_join_num = stats_cum_join_num
        self._leader_cache = _SlideCache(
                leader_join_index, max_stats_windows_size
            )
        self._follower_cache = _SlideCache(
                follower_join_index, max_stats_windows_size
            )

    def fill_leader_example_ids(self, eids):
        evict_hids = self._fill_example_ids(eids, self._leader_cache)
        for hid in evict_hids:
            if self._follower_cache[hid] > 0:
                self._stats_cum_join_num += 1

    def fill_follower_example_ids(self, eids):
        evict_hids = self._fill_example_ids(eids, self._follower_cache)
        for hid in evict_hids:
            self._stats_cum_join_num += self._leader_cache[hid]

    def calc_stats_joined_num(self):
        joined_num = 0
        for hid in self._leader_cache:
            if self._follower_cache[hid] > 0:
                joined_num += 1
        return self._stats_cum_join_num + \
                joined_num * JoinerStats._SampleRateReciprocal

    def get_leader_stats_index(self):
        return self._leader_cache.get_stats_index()

    def get_follower_stats_index(self):
        return self._follower_cache.get_stats_index()

    def _fill_example_ids(self, eids, slide_cache):
        sampled_hids = []
        max_idx = -1
        for idx, eid in eids:
            if idx <= slide_cache.get_stats_index():
                continue
            max_idx = idx
            hkey = '{}{}'.format(self._hash_prefix, eid)
            hid = CityHash64(hkey)
            if hid % JoinerStats._SampleRateReciprocal == 0:
                sampled_hids.append(hid)
        if max_idx >= 0:
            return slide_cache.fill_hash_ids(max_idx, sampled_hids)
        return []
