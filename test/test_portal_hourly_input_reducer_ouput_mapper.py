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

import os
import unittest
from datetime import datetime
import random

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from cityhash import CityHash32

from fedlearner.data_join.portal_hourly_input_reducer import \
        PotralHourlyInputReducer
from fedlearner.data_join.portal_hourly_output_mapper import \
        PotralHourlyOutputMapper
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import common

class TestPotralHourlyReducerMapper(unittest.TestCase):
    def _generate_one_part(self, partition_id):
        item_step = self._portal_manifest.input_partition_num
        cands = list(range(partition_id, self._total_item_num, item_step))
        for i in range(len(cands)):
            if random.randint(1, 4) > 2:
                continue
            a = random.randint(i-16, i+16)
            b = random.randint(i-16, i+16)
            if a < 0:
                a = 0
            if a >= len(cands):
                a = len(cands)-1
            if b < 0:
                b = 0
            if b >= len(cands):
                b = len(cands)-1
            if abs(cands[a]//item_step-b) <= 16 and abs(cands[b]//item_step-a) <= 16:
                cands[a], cands[b] = cands[b], cands[a]
        fpath = common.encode_portal_hourly_fpath(
                self._portal_manifest.input_data_base_dir,
                self._date_time, partition_id
            )
        with tf.io.TFRecordWriter(fpath) as writer:
            for real_id in cands:
                feat = {}
                example_id = '{}'.format(real_id).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id])
                    )
                # if test the basic example_validator for invalid event time
                if real_id == 0 or real_id % 7 != 0:
                    event_time = 150000000 + real_id
                    feat['event_time'] = tf.train.Feature(
                            int64_list=tf.train.Int64List(value=[event_time])
                        )
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                writer.write(example.SerializeToString())

    def _generate_input_data(self):
        self._total_item_num = 1 << 16
        self.assertEqual(self._total_item_num % self._portal_manifest.input_partition_num, 0)
        if gfile.Exists(self._portal_manifest.input_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest.input_data_base_dir)
        if gfile.Exists(self._portal_manifest.output_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest.output_data_base_dir)
        hourly_dir = common.encode_portal_hourly_dir(
                self._portal_manifest.input_data_base_dir,
                self._date_time
            )
        gfile.MakeDirs(hourly_dir)
        for partition_id in range(self._portal_manifest.input_partition_num):
            self._generate_one_part(partition_id)
        succ_tag_fpath = common.encode_portal_hourly_finish_tag(
                self._portal_manifest.input_data_base_dir, self._date_time
            )
        with gfile.GFile(succ_tag_fpath, 'w') as fh:
            fh.write('')

    def _prepare_test(self):
        self._portal_manifest = common_pb.DataJoinPortalManifest(
                name='test_portal',
                input_partition_num=4,
                output_partition_num=8,
                input_data_base_dir='./portal_input',
                output_data_base_dir='./portal_output'
            )
        self._portal_options = dj_pb.DataJoinPotralOptions(
                example_validator=dj_pb.ExampleValidatorOptions(
                    example_validator='EXAMPLE_VALIDATOR',
                    validate_event_time=True,
                ),
                reducer_buffer_size=128,
                raw_data_options=dj_pb.RawDataOptions(
                    raw_data_iter='TF_RECORD'
                ),
                use_mock_etcd=True
            )
        self._date_time = common.convert_timestamp_to_datetime(
                common.trim_timestamp_by_hourly(
                    common.convert_datetime_to_timestamp(datetime.now())
                )
            )
        self._generate_input_data()

    def test_potral_hourly_input_reducer_mapper(self):
        self._prepare_test()
        reducer = PotralHourlyInputReducer(self._portal_manifest,
                                           self._portal_options,
                                           self._date_time)
        mapper = PotralHourlyOutputMapper(self._portal_manifest,
                                          self._portal_options,
                                          self._date_time)
        expected_example_idx = 0
        for tf_item in reducer.make_reducer():
            example_id = '{}'.format(expected_example_idx).encode()
            mapper.map_data(tf_item)
            self.assertEqual(tf_item.example_id, example_id)
            expected_example_idx += 1
            if expected_example_idx % 7 == 0:
                expected_example_idx += 1
        mapper.finish_map()
        for partition_id in range(self._portal_manifest.output_partition_num):
            fpath = common.encode_portal_hourly_fpath(
                    self._portal_manifest.output_data_base_dir,
                    self._date_time, partition_id
                )
            freader = PotralHourlyInputReducer.InputFileReader(partition_id, fpath,
                                                               self._portal_options)
            for example_idx in range(self._total_item_num):
                example_id = '{}'.format(example_idx).encode()
                if example_idx != 0 and (example_idx % 7) == 0:
                    continue
                if partition_id != CityHash32(example_id) % \
                        self._portal_manifest.output_partition_num:
                    continue
                for item in freader:
                    self.assertEqual(example_id,
                                     item.tf_example_item.example_id)
                    break
                self.assertFalse(freader.finished)
            try:
                next(freader)
            except StopIteration:
                self.assertTrue(True)
            else:
                self.assertTrue(False)
            self.assertTrue(freader.finished)

        if gfile.Exists(self._portal_manifest.input_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest.input_data_base_dir)
        if gfile.Exists(self._portal_manifest.output_data_base_dir):
            gfile.DeleteRecursively(self._portal_manifest.output_data_base_dir)

if __name__ == '__main__':
    unittest.main()
