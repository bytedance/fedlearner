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

import random

from tensorflow.compat.v1 import gfile
import tensorflow as tf

from fedlearner.data_join import common

class GenerateTestInputData(object):

    def _get_input_fpath(self, partition_id):
        return "{}/raw_data_partition_{:04}{}".format(self._input_dir,
            partition_id, common.RawDataFileSuffix)

    def _generate_one_partition(self, partition_id, example_id, num_examples):
        fpath = self._get_input_fpath(partition_id)
        with tf.io.TFRecordWriter(fpath) as writer:
            for i in range(num_examples):
                example_id += random.randint(1, 5)
                # real_id = example_id.encode("utf-8")
                event_time = 150000000 + random.randint(10000000, 20000000)
                feat = {}
                feat['example_id'] = tf.train.Feature(bytes_list=
                    tf.train.BytesList(value=[str(example_id).encode('utf-8')]))
                feat['raw_id'] = tf.train.Feature(bytes_list=
                    tf.train.BytesList(value=[str(example_id).encode('utf-8')]))
                feat['event_time'] = tf.train.Feature(int64_list=
                    tf.train.Int64List(value=[event_time]))
                example = tf.train.Example(features=
                    tf.train.Features(feature=feat))
                writer.write(example.SerializeToString())
        return example_id

    def _clean_up(self):
        if gfile.Exists(self._input_dir):
            gfile.DeleteRecursively(self._input_dir)

    def generate_input_data(self):
        self._input_dir = "./data_portal_input_dir"
        self._input_partition_num = 4
        self._partition_item_num = 1 << 16
        self._clean_up()
        gfile.MakeDirs(self._input_dir)
        success_flag_fpath = "{}/_SUCCESS".format(self._input_dir)
        example_id = 1000001
        for partition_id in range(self._input_partition_num):
            example_id = self._generate_one_partition(partition_id, example_id,
                self._partition_item_num)

        with gfile.GFile(success_flag_fpath, 'w') as fh:
            fh.write('')

if __name__ == '__main__':
    g = GenerateTestInputData()
    g.generate_input_data()
