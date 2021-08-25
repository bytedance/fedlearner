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
from collections import OrderedDict
from contextlib import contextmanager

import tensorflow.compat.v1 as tf
import fedlearner.data_join.common as common
from fedlearner.data_join.raw_data_iter_impl.raw_data_iter import RawDataIter


class TfExampleItem(RawDataIter.Item):
    def __init__(self, record_str, cache_type=None, index=None):
        super().__init__()
        self._cache_type = cache_type
        self._index = index
        if self._cache_type:
            assert self._index is not None,\
                    "store space is disk, index cann't be None"
        self._parse_example_error = False
        example = self._parse_example(record_str)
        dic = common.convert_tf_example_to_dict(example)
        # should not be list for data block
        new_dict = {}
        for key, val in dic.items():
            new_dict[key] = val[0] if len(val) == 1 else val
        self._features.update({key: new_dict[key] for key in new_dict
                               if key in common.ALLOWED_FIELDS.keys()})
        self._set_tf_record(record_str)
        self._csv_record = None
        self._gc_example(example)

    @classmethod
    def make(cls, example_id, event_time, raw_id, fname=None, fvalue=None):
        row = OrderedDict()
        row["example_id"] = example_id.decode()
        row["event_time"] = event_time
        if raw_id:
            row["raw_id"] = raw_id
        if fname:
            assert len(fname) == len(fvalue), \
                    "Field name should match field value"
            for i, v in enumerate(fname):
                row[v] = fvalue[i]
        ex = common.convert_dict_to_tf_example(row)
        return cls(ex.SerializeToString())

    @property
    def tf_record(self):
        if self._cache_type:
            return self._cache_type.get_data(self._index)
        return self._record_str

    def _set_tf_record(self, record_str, cache=False):
        # if cache set, we switch the store space to memory
        #  to speed up accessing later
        if self._cache_type and not cache:
            self._record_str = None
            self._cache_type.set_data(self._index, record_str)
        else:
            self._cache_type = None
            self._record_str = record_str

    @property
    def csv_record(self):
        if self._csv_record is None:
            self._csv_record = {}
            example = self._parse_example(self.tf_record)
            if not self._parse_example_error:
                try:
                    self._csv_record = \
                        common.convert_tf_example_to_dict(example)
                except Exception as e: # pylint: disable=broad-except
                    logging.error("Failed convert tf example to csv record, "\
                                  "reason %s", e)
            self._gc_example(example)
        return self._csv_record

    def add_extra_fields(self, additional_records, cache=False):
        example = self._parse_example(self.tf_record)
        if example is not None:
            feat = example.features.feature
            for name, value in additional_records.items():
                if name not in common.ALLOWED_FIELDS:
                    continue
                self._features.update({name: value})
                if common.ALLOWED_FIELDS[name].type is bytes:
                    if isinstance(value, str):
                        value = value.encode()
                    feat[name].CopyFrom(tf.train.Feature(
                                bytes_list=tf.train.BytesList(value=[value])
                            )
                        )
                elif common.ALLOWED_FIELDS[name].type is float:
                    feat[name].CopyFrom(tf.train.Feature(
                        float_list=tf.train.FloatList(value=[value]))
                    )
                else:
                    assert common.ALLOWED_FIELDS[name].type is int
                    feat[name].CopyFrom(tf.train.Feature(
                    int64_list=tf.train.Int64List(value=[value]))
                    )
            self._set_tf_record(example.SerializeToString(), cache)
            if self._csv_record is not None:
                self._csv_record = None
        self._gc_example(example)

    def _parse_example(self, record_str):
        try:
            if not self._parse_example_error:
                example = tf.train.Example()
                example.ParseFromString(record_str)
                return example
        except Exception as e: # pylint: disable=broad-except
            logging.error("Failed parse tf.Example from record %s, reason %s",
                          record_str, e)
            self._parse_example_error = True
        return None

    @staticmethod
    def _gc_example(example):
        if example is not None:
            example.Clear()
            del example

    def clear(self):
        if self._cache_type:
            self._cache_type.delete(self._index)
        del self._record_str
        del self._csv_record


class TfRecordIter(RawDataIter):
    @classmethod
    def name(cls):
        return 'TF_RECORD'

    @contextmanager
    def _data_set(self, fpath):
        data_set = None
        expt = None
        try:
            data_set = tf.data.TFRecordDataset(
                    [fpath],
                    compression_type=self._options.compressed_type,
                    num_parallel_reads=1,
                    buffer_size=None if self._options.read_ahead_size <= 0 \
                            else self._options.read_ahead_size
                )
            batch_size = self._options.read_batch_size if \
                    self._options.read_batch_size > 0 else 1
            data_set = data_set.batch(batch_size)
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
                    if not self._validator.check_tfrecord(raw_data):
                        continue
                    index = self._index
                    if index is None:
                        index = 0
                    yield TfExampleItem(raw_data,
                                        self._cache_type, index)

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None
