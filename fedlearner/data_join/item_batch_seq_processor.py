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

class ItemBatch(object):
    def append(self, item):
        raise NotImplementedError(
                "append is not implemented in base ItemBatch"
            )

    @property
    def begin_index(self):
        raise NotImplementedError(
                "begin_index is not implemented in base ItemBatch"
            )

    def __len__(self):
        raise NotImplementedError(
                "__len__ is not implemented in base ItemBatch"
            )

    def __lt__(self, other):
        raise NotImplementedError(
                "__lt__ is not implemented in base ItemBatch"
            )

    def __iter__(self):
        raise NotImplementedError(
                "__iter__ is not implemented in base ItemBatch"
            )

class ItemBatchSeqProcessor(object):
    def __init__(self, max_flying_item):
        self._lock = threading.Lock()
        self._max_flying_item = max_flying_item
        self._flying_item_count = 0
        self._batch_queue = []
        self._input_finished = False
        self._process_finished = False
        self._last_index = None

    def need_process(self, next_index):
        with self._lock:
            if next_index is None:
                return False
            if self._process_finished and \
                    self._last_index is not None and \
                    next_index > self._last_index:
                return False
            if self._check_index_rollback(next_index):
                return True
            return self._flying_item_count < self._max_flying_item

    def set_input_finished(self):
        with self._lock:
            self._input_finished = True

    def is_input_finished(self):
        with self._lock:
            return self._input_finished

    def get_flying_item_count(self):
        with self._lock:
            return self._flying_item_count

    def get_flying_begin_index(self):
        with self._lock:
            return None if len(self._batch_queue) == 0 \
                    else self._batch_queue[0].begin_index

    def get_process_finished(self):
        with self._lock:
            return self._process_finished

    @classmethod
    def name(cls):
        return 'ItemBatchSeqProcessor'

    def _make_item_batch(self, begin_index):
        raise NotImplementedError("_make_item_batch is not implemented "\
                                  "in basic ItemBatchFetcher")

    def make_processor(self, next_index):
        input_finished = False
        with self._lock:
            if next_index is None:
                return
            if self._check_index_rollback(next_index):
                self._batch_queue = []
                self._flying_item_count = 0
            if len(self._batch_queue) > 0:
                end_batch = self._batch_queue[-1]
                next_index = end_batch.begin_index + len(end_batch)
            input_finished = self._input_finished
        assert next_index >= 0, "the next index should >= 0"
        end_batch = None
        batch_finished = False
        for batch, batch_finished in self._make_inner_generator(next_index):
            if batch is None:
                continue
            if len(batch) > 0:
                self._append_next_item_batch(batch)
                yield batch
            self._update_last_index(batch.begin_index+len(batch)-1)
        if input_finished and batch_finished:
            self._set_process_finished()

    def _make_inner_generator(self, next_index):
        raise NotImplementedError("_make_inner_generator is not "\
                                  "implemented in basic ItemBatchProcessor")

    def fetch_item_batch_by_index(self, next_index, hint_idx=None):
        with self._lock:
            if next_index is None:
                return False, None, hint_idx
            if self._process_finished and \
                    self._last_index is not None and \
                    self._last_index < next_index:
                return True, None, None
            if len(self._batch_queue) == 0:
                return False, None, 0
            end_batch = self._batch_queue[-1]
            # fast path, use the hit
            if hint_idx is not None:
                if hint_idx < len(self._batch_queue):
                    if self._batch_queue[hint_idx].begin_index == next_index:
                        return False, self._batch_queue[hint_idx], hint_idx
                elif next_index >= end_batch.begin_index + len(end_batch):
                    return self._process_finished, None, hint_idx
            fake_batch = self._make_item_batch(next_index)
            idx = bisect.bisect_left(self._batch_queue, fake_batch)
            if idx == len(self._batch_queue):
                if end_batch.begin_index + len(end_batch) >= next_index:
                    return self._process_finished, None, len(self._batch_queue)
            elif self._batch_queue[idx].begin_index == next_index:
                return False, self._batch_queue[idx], idx
            logging.warning("%s next_index %d rollback! check it",
                            self.name(), next_index)
            return False, None, None

    def evict_staless_item_batch(self, staless_index):
        with self._lock:
            skip_batch = 0
            while staless_index is not None and \
                    len(self._batch_queue) > skip_batch:
                batch = self._batch_queue[skip_batch]
                if batch.begin_index + len(batch) -1 <= staless_index:
                    skip_batch += 1
                    self._flying_item_count -= len(batch)
                else:
                    break
            self._batch_queue = self._batch_queue[skip_batch:]
            return skip_batch

    def _append_next_item_batch(self, next_batch):
        with self._lock:
            if len(self._batch_queue) > 0:
                end_batch = self._batch_queue[-1]
                expected_index = end_batch.begin_index + len(end_batch)
                if expected_index != next_batch.begin_index:
                    logging.fatal("%s: next batch index is not consecutive!"\
                                  "%d(expected_index) != %d(supply_index)",
                                  self.name(), expected_index,
                                  next_batch.begin_index)
                    os._exit(-1) # pylint: disable=protected-access
            self._batch_queue.append(next_batch)
            self._flying_item_count += len(next_batch)

    def _check_index_rollback(self, next_index):
        assert next_index is not None
        if len(self._batch_queue) == 0:
            return True
        end_batch = self._batch_queue[-1]
        # fast path check index consecutively
        if next_index == end_batch.begin_index + len(end_batch):
            return False
        # slow path since need binary search
        fake_batch = self._make_item_batch(next_index)
        idx = bisect.bisect_left(self._batch_queue, fake_batch)
        if idx == len(self._batch_queue):
            return next_index != end_batch.begin_index + len(end_batch)
        return self._batch_queue[idx].begin_index != next_index

    def _fly_item_full(self):
        with self._lock:
            return self._flying_item_count > self._max_flying_item

    def _update_last_index(self, last_index):
        with self._lock:
            if self._last_index is None or last_index > self._last_index:
                self._last_index = last_index

    def _set_process_finished(self):
        with self._lock:
            assert self._input_finished
            self._process_finished = True
