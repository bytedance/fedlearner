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
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import unittest
import tensorflow.compat.v1 as tf
import numpy as np

import fedlearner_trainer as bft

class TestDataBlockLoader(unittest.TestCase):
    def test_data_block_loader(self):
        bridge_l = bft.bridge.Bridge('leader', 50051, 'localhost:50052')
        bridge_f = bft.bridge.Bridge('follower', 50052, 'localhost:50051')

        path_l = os.path.join(os.path.dirname(__file__), 'data/leader')
        path_f = os.path.join(os.path.dirname(__file__), 'data/follower')

        tm_l = bft.trainer_master.LocalTrainerMasterClient('leader', path_l)
        tm_f = bft.trainer_master.LocalTrainerMasterClient('leader', path_f)

        dataset_l = bft.data.DataBlockLoader(256, 'leader', bridge_l, tm_l)
        dataset_f = bft.data.DataBlockLoader(256, 'follower', bridge_f, tm_f)

        bridge_l.connect()
        bridge_f.connect()

        g_l = tf.Graph()
        with g_l.as_default():
            record_l = dataset_l.make_batch_iterator().get_next()

        g_f = tf.Graph()
        with g_f.as_default():
            record_f = dataset_f.make_batch_iterator().get_next()

        with tf.Session(graph=g_l) as sess_l:
            try:
                while True:
                    sess_l.run(record_l)
            except tf.errors.OutOfRangeError:
                pass
            sess_l.close()

        with tf.Session(graph=g_f) as sess_f:
            try:
                while True:
                    sess_f.run(record_f)
            except tf.errors.OutOfRangeError:
                pass
            sess_f.close()

        bridge_f.terminate()
        bridge_l.terminate()


if __name__ == '__main__':
        unittest.main()
