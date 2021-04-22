# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

import unittest
import tensorflow.compat.v1 as tf

from fedlearner.data_join.raw_data_iter_impl.validator import Validator


class TestInputDataValidator(unittest.TestCase):

    def test_check_csv(self):
        validator = Validator(sample_ratio=1.0)

        records = [
            ({"example_id": "20200102"}, True),
            ({"example_id": "20200102", "event_time": 123}, True),
            ({"example_id": "20200102", "event_time": 123.}, False),
            ({"example_id": "20200102", "event_time": "123"}, True),
            ({"example_id": "20200102", "event_time": "123."}, False),
            ({"example_id_t": "20200102", "event_time": "123"}, False),
        ]
        for record_tuple in records:
            self.assertEqual(validator.check_csv_record(record_tuple[0]),
                             record_tuple[1])

        record = {"example_id": "20200102", "event_time": "123"}
        self.assertFalse(validator.check_csv_record(record, 3))

    @staticmethod
    def _generate_tfrecord(has_example_id=True, wrong_event_time=False):
        example_id = 10001
        feat = {}
        if has_example_id:
            feat['example_id'] = tf.train.Feature(
                bytes_list=tf.train.BytesList(
                    value=[str(example_id).encode('utf-8')]))
        feat['raw_id'] = tf.train.Feature(
            bytes_list=tf.train.BytesList(
                value=[str(example_id).encode('utf-8')]))
        if wrong_event_time:
            event_time = 150000000.
            feat['event_time'] = tf.train.Feature(
                float_list=tf.train.FloatList(value=[event_time]))
        else:
            event_time = 150000000
            feat['event_time'] = tf.train.Feature(
                int64_list=tf.train.Int64List(value=[event_time]))
        example = tf.train.Example(features=tf.train.Features(feature=feat))
        return example.SerializeToString()

    def test_check_tfrecord(self):
        validator = Validator(sample_ratio=1.0)

        records = [
            (self._generate_tfrecord(), True),
            (self._generate_tfrecord(False), False),
            (self._generate_tfrecord(wrong_event_time=True), False),
        ]
        for record_tuple in records:
            self.assertEqual(validator.check_tfrecord(record_tuple[0]),
                             record_tuple[1])


if __name__ == '__main__':
    unittest.main()
