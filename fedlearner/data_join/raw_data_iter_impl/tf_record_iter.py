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
from contextlib import contextmanager

import tensorflow as tf

from fedlearner.data_join.raw_data_iter_impl.raw_data_iter import RawDataIter

from fedlearner.data_join.common import make_tf_record_iter

class TfExampleItem(RawDataIter.Item):
    def __init__(self, record_str):
        example = tf.train.Example()
        example.ParseFromString(record_str)
        self._record_str = record_str
        self._example = example

    @property
    def example_id(self):
        feat = self._example.features.feature
        return feat['example_id'].bytes_list.value[0]

    @property
    def event_time(self):
        feat = self._example.features.feature
        if feat['event_time'].HasField('int64_list'):
            return feat['event_time'].int64_list.value[0]
        try:
            if feat['event_time'].HasField('bytes_list'):
                return int(feat['event_time'].bytes_list.value[0])
        except Exception as e: # pylint: disable=broad-except
            logging.fatal(
                    "Failed parse %s to event time, reason %s",
                    feat['event_time'].bytes_list.value[0], e
                )
        else:
            logging.fatal("Type of 'event_time' is float, Not allowed!")
        os._exit(-1) # pylint: disable=protected-access
        return None

    @property
    def record(self):
        return self._record_str


class TfDataSetIter(RawDataIter):
    @classmethod
    def name(cls):
        return 'TF_DATASET'

    def __init__(self, options):
        super(TfDataSetIter, self).__init__()
        self._compressed_type = options.get_compressed_type()

    @contextmanager
    def _data_set(self, fpath):
        data_set = None
        try:
            data_set = tf.data.TFRecordDataset(
                    [fpath], compression_type=self._compressed_type,
                    num_parallel_reads=4
                )
            data_set = data_set.batch(64)
            yield data_set
        except Exception as e: # pylint: disable=broad-except
            logging.warning("Failed to access file: %s, reason %s", fpath, e)
        del data_set

    def _inner_iter(self, fpath):
        with self._data_set(fpath) as data_set:
            for batch in iter(data_set):
                for raw_data in batch.numpy():
                    yield TfExampleItem(raw_data)

    def _reset_iter(self, raw_data_rep):
        if raw_data_rep is not None:
            fpath = raw_data_rep.raw_data_path
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

    def __init__(self, options):
        super(TfRecordIter, self).__init__()

    def _inner_iter(self, fpath):
        with make_tf_record_iter(fpath) as record_iter:
            for record in record_iter:
                yield TfExampleItem(record)

    def _reset_iter(self, raw_data_rep):
        if raw_data_rep is not None:
            fpath = raw_data_rep.raw_data_path
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None

    def _next(self):
        assert self._fiter is not None
        return next(self._fiter)
