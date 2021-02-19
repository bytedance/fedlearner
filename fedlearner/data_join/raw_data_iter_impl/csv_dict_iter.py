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

import csv
import io
import logging
import os
import traceback
from collections import OrderedDict

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

import fedlearner.data_join.common as common
from fedlearner.data_join.raw_data_iter_impl.raw_data_iter import RawDataIter


class CsvItem(RawDataIter.Item):
    def __init__(self, raw):
        super().__init__()
        self._features.update(raw)
        self._tf_record = None

    @classmethod
    def make(cls, example_id, event_time, raw_id, fname=None, fvalue=None):
        raw = OrderedDict()
        raw["example_id"] = example_id
        raw["event_time"] = event_time
        raw["raw_id"] = raw_id
        if fname:
            assert len(fname) == len(fvalue), \
                    "Field name should match field value"
            for i, v in enumerate(fname):
                raw[v] = fvalue[i]
        return cls(raw)

    @property
    def example_id(self):
        if 'example_id' not in self._features:
            logging.error("Failed parse example id since no join "\
                          "id in csv dict raw %s", self._features)
            return common.InvalidExampleId
        return str(self._features['example_id']).encode()

    @property
    def click_id(self):
        if 'click_id' not in self._features:
            logging.error("Failed parse click id since no join "\
                          "id in csv dict raw %s", self._features)
            return common.InvalidExampleId
        return self._features['click_id']

    @property
    def event_time(self):
        if 'event_time' in self._features:
            try:
                return int(self._features['event_time'])
            except Exception as e: # pylint: disable=broad-except
                logging.error("Failed to parse event time as int type from "\
                              "%s, reason: %s", self._features['event_time'], e)
        return common.InvalidEventTime

    @property
    def event_time_deep(self):
        if 'event_time_deep' in self._features:
            try:
                return int(self._features['event_time_deep'])
            except Exception as e: # pylint: disable=broad-except
                logging.error("Failed to parse deep event time as int type "\
                              "from %s, reason: %s",
                              self._features['event_time_deep'], e)
        return common.InvalidEventTime

    @property
    def raw_id(self):
        if 'raw_id' not in self._features:
            logging.error("Failed parse raw id since no join "\
                          "id in csv dict raw %s", self._features)
            return common.InvalidRawId
        return str(self._features['raw_id']).encode()

    @property
    def record(self):
        return self._features

    @property
    def tf_record(self):
        if self._tf_record is None:
            try:
                example = common.convert_dict_to_tf_example(self._features)
                self._tf_record = example.SerializeToString()
            except Exception as e: # pylint: disable=broad-except
                traceback.print_exc()
                logging.error("Failed convert csv dict to tf example, "\
                              "reason %s", e)
                self._tf_record = tf.train.Example().SerializeToString()
        return self._tf_record

    @property
    def csv_record(self):
        return self._features

    def set_example_id(self, example_id):
        new_features = OrderedDict({'example_id': example_id})
        new_features.update(self._features)
        self._features = new_features
        if self._tf_record is not None:
            self._tf_record = None


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
                dict_reader, rest_buffer, read_finished = \
                        self._make_csv_dict_reader(fh, rest_buffer,
                                                   aware_headers)
                aware_headers = False
                if self._headers is None:
                    self._headers = dict_reader.fieldnames
                elif self._headers != dict_reader.fieldnames:
                    logging.fatal("the schema of %s is %s, mismatch "\
                                  "with previous %s", fpath,
                                  self._headers, dict_reader.fieldnames)
                    traceback.print_stack()
                    os._exit(-1) # pylint: disable=protected-access
                for raw in dict_reader:
                    yield CsvItem(raw)

    def _make_csv_dict_reader(self, fh, rest_buffer, aware_headers):
        if self._options.read_ahead_size <= 0:
            assert aware_headers
            return csv.DictReader(fh), [], True
        read_buffer = fh.read(self._options.read_ahead_size)
        read_finished = len(read_buffer) < self._options.read_ahead_size
        idx = read_buffer.rfind('\n')
        if read_finished:
            idx = len(read_buffer) - 1
        elif idx == -1 and len(read_buffer) > 0:
            logging.fatal("not meet line break in size %d",
                          self._options.read_ahead_size)
            traceback.print_stack()
            os._exit(-1) # pylint: disable=protected-access
        str_buffer = read_buffer[0:idx+1] if len(rest_buffer) == 0 \
                        else rest_buffer+read_buffer[0:idx+1]
        if aware_headers:
            return csv.DictReader(io.StringIO(str_buffer)), \
                    read_buffer[idx+1:], read_finished
        assert self._headers is not None
        return csv.DictReader(io.StringIO(str_buffer),
                              fieldnames=self._headers), \
                read_buffer[idx+1:], read_finished

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None
