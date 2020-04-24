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
import bisect
import logging
import os

from contextlib import contextmanager

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.raw_data_visitor import RawDataVisitor

class ExampleIdBatchFetcher(object):
    class ExampleIdBatch(object):
        def __init__(self, partition_id, begin_index):
            self._lite_example_ids = dj_pb.LiteExampleIds(
                    partition_id=partition_id,
                    begin_index=begin_index
                )

        def append(self, example_id, event_time):
            self._lite_example_ids.example_id.append(example_id)
            self._lite_example_ids.event_time.append(event_time)

        @property
        def begin_index(self):
            return self._lite_example_ids.begin_index

        @property
        def lite_example_ids(self):
            return self._lite_example_ids

        @property
        def partition_id(self):
            return self._lite_example_ids.partition_id

        def __len__(self):
            return len(self._lite_example_ids.example_id)

        def __lt__(self, other):
            assert isinstance(other, ExampleIdBatchFetcher.ExampleIdBatch)
            assert self.partition_id == other.partition_id
            return self.begin_index < other.begin_index

    def __init__(self, etcd, data_source, partition_id,
                 raw_data_options, example_id_batch_options):
        self._lock = threading.Lock()
        self._partition_id = partition_id
        self._raw_data_visitor = RawDataVisitor(
                etcd, data_source, partition_id, raw_data_options
            )
        self._example_id_batch_options = example_id_batch_options
        self._flying_example_id_count = 0
        self._batch_queue = []
        self._raw_data_finished = False
        self._fetch_finished = False
        self._last_index = None

    def need_fetch(self, next_index):
        with self._lock:
            if next_index is None:
                return False
            if self._last_index is not None and next_index > self._last_index:
                assert self._fetch_finished
                return False
            if self._check_index_rollback(next_index):
                return True
            return self._flying_example_id_count < \
                    self._example_id_batch_options.max_flying_example_id

    def set_raw_data_finished(self):
        with self._lock:
            self._raw_data_finished = True

    def is_raw_data_finished(self):
        with self._lock:
            return self._raw_data_finished

    @contextmanager
    def make_fetcher(self, next_index):
        yield self._inner_fetcher(next_index)

    def _inner_fetcher(self, next_index):
        raw_data_finished = False
        with self._lock:
            if next_index is None:
                return
            if self._check_index_rollback(next_index):
                self._batch_queue = []
                self._flying_example_id_count = 0
            if len(self._batch_queue) > 0:
                end_batch = self._batch_queue[-1]
                next_index = end_batch.begin_index + len(end_batch)
            raw_data_finished = self._raw_data_finished
        assert next_index >= 0, "the next index should >= 0"
        self._raw_data_visitor.active_visitor()
        if next_index == 0:
            self._raw_data_visitor.reset()
        else:
            self._raw_data_visitor.seek(next_index - 1)
        while not self._raw_data_visitor.finished() and \
                not self._fly_example_id_full():
            next_batch = ExampleIdBatchFetcher.ExampleIdBatch(
                    self._partition_id, next_index
                )
            for (index, item) in self._raw_data_visitor:
                if index != next_index:
                    logging.fatal("index is for partition %d not consecutive, "\
                                  "%d != %d",
                                  self._partition_id, index, next_index)
                    os._exit(-1) # pylint: disable=protected-access
                next_batch.append(item.example_id, item.event_time)
                next_index += 1
                if len(next_batch) > \
                        self._example_id_batch_options.example_id_batch_size:
                    break
            if len(next_batch) > 0:
                self._append_new_example_id_batch(next_batch)
                yield next_batch
        if raw_data_finished and self._raw_data_visitor.finished():
            self._set_fetch_finished(self._raw_data_visitor.get_index())

    def fetch_example_id_batch_by_index(self, next_index, hit_idx=None):
        with self._lock:
            if next_index is None:
                return False, None, hit_idx
            if self._last_index is not None and self._last_index < next_index:
                assert self._fetch_finished
                return True, None, None
            if len(self._batch_queue) == 0:
                return False, None, 0
            end_batch = self._batch_queue[-1]
            # fast path, use the hit
            if hit_idx is not None:
                if hit_idx < len(self._batch_queue):
                    if self._batch_queue[hit_idx].begin_index == next_index:
                        return False, self._batch_queue[hit_idx], hit_idx
                elif next_index >= end_batch.begin_index + len(end_batch):
                    return self._fetch_finished, None, hit_idx
            fake_batch = ExampleIdBatchFetcher.ExampleIdBatch(
                    self._partition_id, next_index
                )
            idx = bisect.bisect_left(self._batch_queue, fake_batch)
            if idx == len(self._batch_queue):
                if end_batch.begin_index + len(end_batch) >= next_index:
                    return self._fetch_finished, None, len(self._batch_queue)
            elif self._batch_queue[idx].begin_index == next_index:
                return False, self._batch_queue[idx], idx
            logging.warning("next_index %d rollback! check it", next_index)
            return False, None, None

    def evict_staless_example_id_batch(self, dumped_index):
        with self._lock:
            skip_batch = 0
            while dumped_index is not None and \
                    len(self._batch_queue) > skip_batch:
                batch = self._batch_queue[skip_batch]
                if batch.begin_index + len(batch) -1 <= dumped_index:
                    skip_batch += 1
                    self._flying_example_id_count -= len(batch)
                else:
                    break
            self._batch_queue = self._batch_queue[skip_batch:]
            return skip_batch

    def _append_new_example_id_batch(self, next_batch):
        with self._lock:
            if len(self._batch_queue) > 0:
                end_batch = self._batch_queue[-1]
                expected_index = end_batch.begin_index + len(end_batch)
                if expected_index != next_batch.begin_index:
                    logging.fatal("next batch index is not consecutive!"\
                                  "%d(expected_index) != %d(supply_index)",
                                  expected_index, next_batch.begin_index)
                    os._exit(-1) # pylint: disable=protected-access
            self._batch_queue.append(next_batch)
            self._flying_example_id_count += len(next_batch)

    def _check_index_rollback(self, next_index):
        assert next_index is not None
        if len(self._batch_queue) == 0:
            return True
        end_batch = self._batch_queue[-1]
        # fast path check index consecutively
        if next_index == end_batch.begin_index + len(end_batch):
            return False
        # slow path since need binary search
        fake_batch = ExampleIdBatchFetcher.ExampleIdBatch(
                self._partition_id, next_index
            )
        idx = bisect.bisect_left(self._batch_queue, fake_batch)
        if idx == len(self._batch_queue):
            return next_index != end_batch.begin_index + len(end_batch)
        return self._batch_queue[idx].begin_index != next_index

    def _fly_example_id_full(self):
        with self._lock:
            return self._flying_example_id_count > \
                    self._example_id_batch_options.max_flying_example_id

    def _set_fetch_finished(self, last_index):
        with self._lock:
            self._fetch_finished = True
            self._last_index = last_index
