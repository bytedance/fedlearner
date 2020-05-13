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

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

import fedlearner.data_join.common as common
from fedlearner.data_join.raw_data_iter_impl.raw_data_iter import RawDataIter

class CsvItem(RawDataIter.Item):
    def __init__(self, raw):
        self._raw = raw
        self._tf_record = None

    @property
    def example_id(self):
        if 'example_id' not in self._raw:
            logging.error("Failed parse example id since no join "\
                          "id in csv dict raw %s", self._raw)
            return common.InvalidExampleId
        if isinstance(self._raw['example_id'], bytes):
            return self._raw['example_id']
        return str(self._raw['example_id']).encode()

    @property
    def event_time(self):
        if 'event_time' in self._raw:
            try:
                return int(self._raw['event_time'])
            except Exception as e: # pylint: disable=broad-except
                logging.error("Failed to parse event time as int "\
                              "type from %s", self._raw['event_time'])
        return common.InvalidEventTime

    @property
    def raw_id(self):
        if 'raw_id' not in self._raw:
            logging.error("Failed parse raw id since no join "\
                          "id in csv dict raw %s", self._raw)
            return ''
        if isinstance(self._raw['raw_id'], bytes):
            return self._raw['raw_id']
        return str(self._raw['raw_id']).encode()

    @property
    def record(self):
        return self._raw

    @property
    def tf_record(self):
        if self._tf_record is None:
            try:
                example = common.convert_dict_to_tf_example(self._raw)
                self._tf_record = example.SerializeToString()
            except Exception as e: # pylint: disable=broad-except
                logging.error("Failed convert csv dict to tf example, "\
                              "reason %s", e)
                self._tf_record = tf.train.Example().SerializeToString()
        return self._tf_record

    @property
    def csv_record(self):
        return self._raw

class CsvDictIter(RawDataIter):
    def __init__(self, options):
        super(CsvDictIter, self).__init__(options)
        self._headers = None

    @classmethod
    def name(cls):
        return 'CSV_DICT'

    def _inner_iter(self, fpath):
        with gfile.Open(fpath, 'r') as f:
            dict_reader = csv.DictReader(f)
            if self._headers is None:
                self._headers = dict_reader.fieldnames
            elif self._headers != dict_reader.fieldnames:
                logging.fatal("the schema of %s is %s, mismatch with "\
                              "previous %s", fpath,
                              self._headers, dict_reader.fieldnames)
                os._exit(-1) # pylint: disable=protected-access
            for raw in dict_reader:
                yield CsvItem(raw)

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None
