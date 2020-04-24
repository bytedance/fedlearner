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

try:
    import queue
except ImportError:
    import Queue as queue
import logging
import random
from datetime import datetime

from tensorflow.compat.v1 import gfile

from fedlearner.data_join import common, visitor
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfRecordIter
from fedlearner.data_join.example_validate_impl import create_example_validator

class PotralHourlyInputReducer(object):
    class RecordItem(object):
        def __init__(self, partition_id, tf_example_item):
            self._partition_id = partition_id
            self._tf_example_item = tf_example_item

        @property
        def partition_id(self):
            return self._partition_id

        @property
        def tf_example_item(self):
            return self._tf_example_item

        def __lt__(self, other):
            assert isinstance(other, PotralHourlyInputReducer.RecordItem)
            return self._tf_example_item.event_time < \
                    other.tf_example_item.event_time

    class InputFileReader(object):
        def __init__(self, partition_id, fpath, portal_options):
            self._partition_id = partition_id
            self._fpath = fpath
            self._raw_data_options = portal_options.raw_data_options
            self._example_validator = create_example_validator(
                    portal_options.example_validator
                )
            self._fiter = None
            if gfile.Exists(fpath):
                self._finished = False
            else:
                self._finished = True

        @property
        def finished(self):
            return self._finished

        def __iter__(self):
            return self

        def __next__(self):
            return self._next_internal()

        def next(self):
            return self._next_internal()

        def _next_internal(self):
            if not self._finished:
                try:
                    while True:
                        tf_item = None
                        if self._fiter is None:
                            self._fiter = TfRecordIter(self._raw_data_options)
                            meta = visitor.IndexMeta(0, 0, self._fpath)
                            self._fiter.reset_iter(meta, True)
                            tf_item = self._fiter.get_item()
                        else:
                            _, tf_item = next(self._fiter)
                        valid, reason = \
                            self._example_validator.validate_example(tf_item)
                        if valid:
                            return PotralHourlyInputReducer.RecordItem(
                                    self._partition_id, tf_item
                                )
                        logging.warning("skip record in %s, reason %s",
                                        self._fpath, reason)
                except StopIteration:
                    self._finished = True
            raise StopIteration("%s has been iter finished" % self._fpath)

    def __init__(self, potral_manifest, potral_options, date_time):
        assert isinstance(date_time, datetime)
        self._potral_manifest = potral_manifest
        self._potral_options = potral_options
        self._readers = []
        self._date_time = date_time
        self._active_partition = set()
        self._pque = queue.PriorityQueue(potral_options.reducer_buffer_size)
        for partition_id in range(self.input_partition_num):
            fpath = common.encode_portal_hourly_fpath(
                    self._potral_manifest.input_data_base_dir,
                    date_time, partition_id)
            reader = PotralHourlyInputReducer.InputFileReader(
                    partition_id, fpath, self._potral_options
                )
            self._readers.append(reader)
            self._active_partition.add(partition_id)
        self._preload_reduce_buffer()

    def make_reducer(self):
        while not self._pque.empty():
            record_item = self._pque.get()
            self._replenish_item(record_item.partition_id)
            yield record_item.tf_example_item

    def _preload_reduce_buffer(self):
        partition_id = 0
        while not self._pque.full() and len(self._active_partition) > 0:
            if partition_id not in self._active_partition:
                continue
            self._replenish_item(partition_id)
            partition_id = (partition_id + 1) % self.input_partition_num

    def _replenish_item(self, partition_id):
        assert not self._pque.full(), \
            "Priority Queue should not full duration replenish_item"
        while len(self._active_partition) > 0:
            if partition_id in self._active_partition:
                for item in self._readers[partition_id]:
                    self._pque.put(item)
                    return
                assert self._readers[partition_id].finished
                self._active_partition.discard(partition_id)
            if len(self._active_partition) > 0:
                partition_id = random.choice(list(self._active_partition))

    @property
    def input_partition_num(self):
        return self._potral_manifest.input_partition_num
