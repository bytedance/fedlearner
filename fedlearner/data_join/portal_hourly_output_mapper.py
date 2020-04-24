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

import uuid
import os
import logging
from datetime import datetime

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from cityhash import CityHash32 # pylint: disable=no-name-in-module

from fedlearner.data_join import common
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

class PotralHourlyOutputMapper(object):
    class OutputFileWriter(object):
        TMP_COUNTER = 0
        def __init__(self, partition_id, fpath):
            self._partition_id = partition_id
            self._fpath = fpath
            self._tmp_fpath = self._get_tmp_fpath()
            self._tf_record_writer = tf.io.TFRecordWriter(self._tmp_fpath)
            self._record_count = 0

        def append(self, item):
            self._tf_record_writer.write(item.record)
            self._record_count += 1

        def finish(self):
            self._tf_record_writer.close()
            if self._record_count == 0:
                logging.warning("no record in potroal output file " \
                                "%s at partition %d. reomve the tmp " \
                                "file %s", self._fpath, self._partition_id,
                                self._tmp_fpath)
                gfile.Remove(self._tmp_fpath)
            else:
                gfile.Rename(self._tmp_fpath, self._fpath, True)
                logging.warning("dump %d record in potral output file"\
                                " %s at partition %d", self._record_count,
                                self._fpath, self._partition_id)

        def _get_tmp_fpath(self):
            tmp_fname = str(uuid.uuid1()) + '-{}.tmp'.format(self.TMP_COUNTER)
            self.TMP_COUNTER += 1
            return os.path.join(self._get_output_dir(), tmp_fname)

        def _get_output_dir(self):
            return os.path.dirname(self._fpath)

    def __init__(self, potral_manifest, potral_options, date_time):
        assert isinstance(date_time, datetime)
        self._potral_manifest = potral_manifest
        self._potral_options = potral_options
        self._date_time = date_time
        hourly_dir = common.encode_portal_hourly_dir(
                self._potral_manifest.output_data_base_dir,
                date_time
            )
        if not gfile.Exists(hourly_dir):
            gfile.MakeDirs(hourly_dir)
        if not gfile.IsDirectory(hourly_dir):
            logging.fatal("%s must be a directory for mapper output",
                          hourly_dir)
            os._exit(-1) # pylint: disable=protected-access
        self._writers = []
        for partition_id in range(self.output_partition_num):
            fpath = common.encode_portal_hourly_fpath(
                    self._potral_manifest.output_data_base_dir,
                    date_time, partition_id)
            writer = PotralHourlyOutputMapper.OutputFileWriter(
                    partition_id, fpath
                )
            self._writers.append(writer)

    def map_data(self, tf_item):
        assert isinstance(tf_item, TfExampleItem), \
            "the input tf_item should be TfExampleItem"
        example_id = tf_item.example_id
        assert example_id != common.InvalidExampleId
        partition_id = CityHash32(example_id) % self.output_partition_num
        assert partition_id < len(self._writers)
        self._writers[partition_id].append(tf_item)

    def finish_map(self):
        for writer in self._writers:
            writer.finish()
        succ_tag_fpath = common.encode_portal_hourly_finish_tag(
                self._potral_manifest.output_data_base_dir,
                self._date_time
            )
        with gfile.GFile(succ_tag_fpath, 'w') as fh:
            fh.write('')

    @property
    def output_partition_num(self):
        return self._potral_manifest.output_partition_num
