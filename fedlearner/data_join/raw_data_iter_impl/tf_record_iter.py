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
from contextlib import contextmanager

import tensorflow as tf

import fedlearner.data_join.common as common
from fedlearner.data_join.raw_data_iter_impl.raw_data_iter import RawDataIter

class TfExampleItem(RawDataIter.Item):
    def __init__(self, record_str):
        example = tf.train.Example()
        example.ParseFromString(record_str)
        self._record_str = record_str
        self._example = example

    @property
    def example_id(self):
        try:
            feat = self._example.features.feature
            return feat['example_id'].bytes_list.value[0]
        except Exception as e: # pylint: disable=broad-except
            logging.error('Failed to parse example id from %s, reason %s',
                          self._record_str, e)
        return common.InvalidExampleId

    @property
    def event_time(self):
        try:
            feat = self._example.features.feature
            if feat['event_time'].HasField('int64_list'):
                return feat['event_time'].int64_list.value[0]
            if feat['event_time'].HasField('bytes_list'):
                return int(feat['event_time'].bytes_list.value[0])
        except Exception as e: # pylint: disable=broad-except
            logging.error("Failed parse event time from %s, reason %s",
                          self._record_str, e)
        return common.InvalidEventTime

    @property
    def record(self):
        return self._record_str


class TfDataSetIter(RawDataIter):
    @classmethod
    def name(cls):
        return 'TF_DATASET'

    @contextmanager
    def _data_set(self, fpath):
        data_set = None
        expt = None
        try:
            data_set = tf.data.TFRecordDataset(
                    [fpath],
                    compression_type=self._options.compressed_type,
                    num_parallel_reads=4
                )
            data_set = data_set.batch(64)
            yield data_set
        except Exception as e: # pylint: disable=broad-except
            logging.warning("Failed to access file: %s, reason %s", fpath, e)
            expt = e
        if data_set is not None:
            del data_set
        if expt is not None:
            raise expt

    def _inner_iter(self, fpath):
        with self._data_set(fpath) as data_set:
            for batch in iter(data_set):
                for raw_data in batch.numpy():
                    yield TfExampleItem(raw_data)

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None

    def _next(self):
        assert self._fiter is not None
        return next(self._fiter)


class TfRecordIter(RawDataIter):
    @classmethod
    def name(cls):
        return 'TF_RECORD'

    def _inner_iter(self, fpath):
        with common.make_tf_record_iter(fpath) as record_iter:
            for record in record_iter:
                yield TfExampleItem(record)

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None

    def _next(self):
        assert self._fiter is not None
        return next(self._fiter)
