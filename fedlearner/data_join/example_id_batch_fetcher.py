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

import tensorflow.compat.v1 as tf

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.raw_data_visitor import RawDataVisitor
from fedlearner.data_join import common as djc

class ExampleIdBatch(ItemBatch):
    def __init__(self, partition_id, begin_index):
        self._partition_id = partition_id
        self._begin_index = begin_index

        self._feature_buf = dict()
        self._key_feature = 'example_id'
        for fn in djc.SYNC_ALLOWED_OPTIONAL_FIELDS:
            self._feature_buf[fn] = []

    def append(self, item):
        for fn in djc.SYNC_ALLOWED_OPTIONAL_FIELDS:
            value = getattr(item, fn, djc.ALLOWED_FIELDS[fn].default_value)
            if value and value != djc.ALLOWED_FIELDS[fn].default_value:
                self._feature_buf[fn].append(value)

    @property
    def begin_index(self):
        return self._begin_index

    def make_packed_lite_example_ids(self):
        features = {}
        for name, value_list in self._feature_buf.items():
            if len(value_list) > 0:
                if isinstance(value_list[0], int):
                    features[name] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=value_list))
                else:
                    features[name] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=value_list))
        tf_features = tf.train.Features(feature=features)
        serde_lite_examples = dj_pb.LiteExampleIds(
            partition_id=self._partition_id,
            begin_index=self._begin_index,
            features=tf_features
        )

        return dj_pb.PackedLiteExampleIds(
                partition_id=self._partition_id,
                begin_index=self._begin_index,
                example_id_num=self.__len__(),
                sered_lite_example_ids=serde_lite_examples.SerializeToString()
            )

    @property
    def partition_id(self):
        return self._partition_id

    def __len__(self):
        return len(self._feature_buf[self._key_feature])

    def __lt__(self, other):
        assert isinstance(other, ExampleIdBatch)
        assert self.partition_id == other.partition_id
        return self.begin_index < other.begin_index

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
