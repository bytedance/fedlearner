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
import csv
import os
import io

import tensorflow.compat.v1 as tf
import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

import fedlearner.data_join.common as common
from fedlearner.data_join.raw_data_iter_impl.raw_data_iter import RawDataIter

class CsvItem(RawDataIter.Item):
    def __init__(self, field_keys, field_vals):
        self._field_keys = field_keys
        self._field_vals = field_vals
        self._tf_record = None
        self._example_id_index = None
        self._event_time_index = None
        self._raw_id_index = None
        self._placed_example_id = None
        self._parse_csv_item()

    @property
    def example_id(self):
        if self._placed_example_id is not None:
            return str(self._placed_example_id).encode()
        if self._example_id_index is not None:
            return str(self._field_vals[self._example_id_index]).encode()
        logging.error("Failed parse example id since no example id "\
                      "in field key: %s, field value: %s",
                      self._field_keys, self._field_vals)
        return common.InvalidExampleId

    @property
    def event_time(self):
        if self._event_time_index is not None:
            assert self._event_time_index < len(self._field_vals)
            try:
                return int(self._field_vals[self._event_time_index])
            except Exception as e: # pylint: disable=broad-except
                logging.error("Failed to parse event time as int type from "\
                              "field key: %s, field val: %s, reason: %s",
                              self._field_keys, self._field_vals, e)
        return common.InvalidEventTime

    @property
    def raw_id(self):
        if self._raw_id_index is not None:
            assert self._raw_id_index < len(self._field_vals)
            return str(self._raw['raw_id']).encode()
        logging.error("Failed parse raw id since no raw "\
                      "id from filed key: %s, field val: %s",
                      self._field_keys, self._field_vals)
        return common.InvalidRawId

    @property
    def record(self):
        return self.csv_record

    @property
    def tf_record(self):
        if self._tf_record is None:
            try:
                rfield_keys = self._field_keys
                rfield_vals = self._field_vals
                if self._placed_example_id is not None:
                    rfield_keys = ['example_id'] + self._field_keys
                    rfield_vals = [self._placed_example_id] + self._field_vals
                example = common.convert_csv_record_to_tf_example(rfield_keys,
                                                                  rfield_vals)
                self._tf_record = example.SerializeToString()
            except Exception as e: # pylint: disable=broad-except
                logging.error("Failed convert csv dict to tf example, "\
                              "reason %s", e)
                self._tf_record = tf.train.Example().SerializeToString()
        return self._tf_record

    @property
    def csv_record(self):
        if self._placed_example_id is not None:
            return ['example_id'] + self._field_keys, \
                    [self._placed_example_id] + self._field_vals
        return self._field_keys, self._field_vals

    def set_example_id(self, example_id):
        self._placed_example_id = example_id
        if self._tf_record is not None:
            self._tf_record = None

    def _parse_csv_item(self):
        assert isinstance(self._field_keys, list) and \
                isinstance(self._field_vals, list) and \
                len(self._field_keys) == len(self._field_vals)
        for idx, field in enumerate(self._field_keys):
            if field == 'example_id':
                self._example_id_index = idx
            if field == 'event_time':
                self._event_time_index = idx
            if field == 'raw_id':
                self._raw_id_index = idx

class CsvDictIter(RawDataIter):
    def __init__(self, options):
        super(CsvDictIter, self).__init__(options)
        self._headers = None

    @classmethod
    def name(cls):
        return 'CSV_DICT'

    def _inner_iter(self, fpath):
        with gfile.Open(fpath, 'r') as fh:
            rest_buffer = []
            aware_headers = True
            read_finished = False
            while not read_finished:
                csv_reader, rest_buffer, read_finished = \
                        self._make_csv_record_reader(fh, rest_buffer)
                if aware_headers:
                    try:
                        csv_headers = next(csv_reader)
                    except StopIteration:
                        logging.warning('%s of csv is empty', fpath)
                        break
                    else:
                        if self._headers is None:
                            self._headers = csv_headers
                        elif self._headers != csv_headers:
                            logging.fatal("the schema of %s is %s, mismatch "\
                                          "with previous %s",
                                          fpath, self._headers, csv_headers)
                            os._exit(-1) # pylint: disable=protected-access
                aware_headers = False
                for fields in csv_reader:
                    yield CsvItem(self._headers, fields)

    def _make_csv_record_reader(self, fh, rest_buffer):
        if self._options.read_ahead_size <= 0:
            return csv.reader, [], True
        read_buffer = fh.read(self._options.read_ahead_size)
        read_finished = len(read_buffer) < self._options.read_ahead_size
        idx = read_buffer.rfind('\n')
        if read_finished:
            idx = len(read_buffer) - 1
        elif idx == -1 and len(read_buffer) > 0:
            logging.fatal("not meet line break in size %d",
                          self._options.read_ahead_size)
            os._exit(-1) # pylint: disable=protected-access
        str_buffer = read_buffer[0:idx+1] if len(rest_buffer) == 0 \
                        else rest_buffer+read_buffer[0:idx+1]
        return csv.reader(io.StringIO(str_buffer)), \
                read_buffer[idx+1:], read_finished

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None
