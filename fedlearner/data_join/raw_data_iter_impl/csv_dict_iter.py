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
        if 'join_id' not in self._raw:
            logging.error("Failed parse example id since no join "\
                          "id in csv dict raw %s", self._raw)
            return common.InvalidExampleId
        if isinstance(self._raw['join_id'], bytes):
            return self._raw['join_id']
        return str(self._raw['join_id']).encode()

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
    @classmethod
    def name(cls):
        return 'CSV_DICT'

    def _inner_iter(self, fpath):
        with gfile.Open(fpath, 'r') as f:
            fsize = gfile.Stat(fpath).length
            f.seek(0 if fsize <= 2048 else fsize-2048, 0)
            lines = f.readlines()
            if len(lines) <= 1:
                logging.fatal("not support length of header of csv "\
                              "file %s is large > 2048.", fpath)
                os._exit(-1) # pylint: disable=protected-access
            f.seek(0, 0)
            end_data_cursor = fsize - len(lines[-1])
            headrs = lines[-1].strip().split(',')
            dict_reader = csv.DictReader(f, fieldnames=headrs)
            for raw in dict_reader:
                if f.tell() > end_data_cursor:
                    break
                yield CsvItem(raw)

    def _reset_iter(self, index_meta):
        if index_meta is not None:
            fpath = index_meta.fpath
            fiter = self._inner_iter(fpath)
            item = next(fiter)
            return fiter, item
        return None, None
