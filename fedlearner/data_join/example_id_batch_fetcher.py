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
import os
import traceback

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.raw_data_visitor import RawDataVisitor

class ExampleIdBatch(ItemBatch):
    def __init__(self, partition_id, begin_index):
        self._partition_id = partition_id
        self._begin_index = begin_index
        self._example_ids = []
        self._event_times = []
        self._id_types = []
        self._event_time_deeps = []
        self._click_ids = []

    def append(self, item):
        self._example_ids.append(item.example_id)
        self._event_times.append(item.event_time)
        if hasattr(item, 'id_type'):
            assert hasattr(item, 'event_time_deep'), "Incomplete new example"
            assert hasattr(item, 'click_id'), "Incomplete new example"
            self._id_types.append(item.id_type)
            self._event_time_deeps.append(item.event_time_deep)
            self._click_ids.append(item.click_id)

    @property
    def begin_index(self):
        return self._begin_index

    def make_packed_lite_example_ids(self):
        serde_lite_examples = dj_pb.LiteExampleIds(
            partition_id=self._partition_id,
            begin_index=self._begin_index,
            example_id=self._example_ids,
            event_time=self._event_times,
        )
        assert len(self._id_types) == len(self._click_ids), \
                "Rawrata invalid new version"
        assert len(self._id_types) == len(self._event_time_deeps), \
                "Rawrata invalid new version"
        if len(self._id_types) > 0:
            serde_lite_examples.id_type = self._id_types
            serde_lite_examples.event_time_deep = self._event_time_deeps
            serde_lite_examples.click_id = self._click_ids
        return dj_pb.PackedLiteExampleIds(
                partition_id=self._partition_id,
                begin_index=self._begin_index,
                example_id_num=len(self._example_ids),
                sered_lite_example_ids=serde_lite_examples.SerializeToString()
            )

    @property
    def partition_id(self):
        return self._partition_id

    def __len__(self):
        return len(self._example_ids)

    def __lt__(self, other):
        assert isinstance(other, ExampleIdBatch)
        assert self.partition_id == other.partition_id
        return self.begin_index < other.begin_index

    def __iter__(self):
        assert len(self._example_ids) == len(self._event_times)
        if len(self._id_types) > 0:
            return iter(zip(
                self._example_ids,
                self._event_times,
                self._id_types,
                self._event_time_deeps,
                self._click_ids
            ))
        return iter(zip(self._example_ids, self._event_times))

class ExampleIdBatchFetcher(ItemBatchSeqProcessor):
    def __init__(self, kvstore, data_source, partition_id,
                 raw_data_options, batch_processor_options):
        super(ExampleIdBatchFetcher, self).__init__(
                batch_processor_options.max_flying_item
            )
        self._raw_data_visitor = RawDataVisitor(
                kvstore, data_source, partition_id, raw_data_options
            )
        self._batch_size = batch_processor_options.batch_size
        self._partition_id = partition_id
        ds_name = data_source.data_source_meta.name
        self._metric_tags = {'data_source_name': ds_name,
                             'partition': self._partition_id}

    @classmethod
    def name(cls):
        return 'ExampleIdBatchFetcher'

    def _make_item_batch(self, begin_index):
        return ExampleIdBatch(self._partition_id, begin_index)

    def _make_inner_generator(self, next_index):
        self._raw_data_visitor.active_visitor()
        if next_index == 0:
            self._raw_data_visitor.reset()
        else:
            self._raw_data_visitor.seek(next_index - 1)
        while not self._raw_data_visitor.finished() and \
                not self._fly_item_full():
            next_batch = self._make_item_batch(next_index)
            for (index, item) in self._raw_data_visitor:
                if index != next_index:
                    logging.fatal("index of raw data visitor for partition "\
                                  "%d is not consecutive, %d != %d",
                                  self._partition_id, index, next_index)
                    traceback.print_stack()
                    os._exit(-1) # pylint: disable=protected-access
                next_batch.append(item)
                next_index += 1
                if len(next_batch) > self._batch_size:
                    break
            yield next_batch, self._raw_data_visitor.finished()
        yield self._make_item_batch(next_index), \
                self._raw_data_visitor.finished()

    def _get_metrics_tags(self):
        return self._metric_tags
