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
import shutil
import numpy as np
import tensorflow as tf

from tensorflow.core.example.example_pb2 import Example
from tensorflow.core.example.feature_pb2 import FloatList, Features, Feature, \
                                                Int64List, BytesList

current_dir = os.path.dirname(__file__)
shutil.rmtree(os.path.join(current_dir, 'data'), ignore_errors=True)
os.makedirs(os.path.join(current_dir, 'data/leader'))
os.makedirs(os.path.join(current_dir, 'data/follower'))


(x, y), _ = tf.keras.datasets.mnist.load_data()

x = x.reshape(x.shape[0], -1).astype(np.float32) / 255.0
y = y.astype(np.int64)

xl = x[:, :x.shape[1]//2]
xf = x[:, x.shape[1]//2:]

N = 10
chunk_size = x.shape[0]//N

for i in range(N):
    filename_l = os.path.join(current_dir, 'data/leader/%02d.tfrecord'%i)
    filename_f = os.path.join(current_dir, 'data/follower/%02d.tfrecord'%i)
    fl = tf.io.TFRecordWriter(filename_l)
    ff = tf.io.TFRecordWriter(filename_f)

    for j in range(chunk_size):
        idx = i*chunk_size + j
        features_l = {}
        features_l['example_id'] = Feature(
            bytes_list=BytesList(value=[str(idx).encode('utf-8')]))
        features_l['y'] = Feature(int64_list=Int64List(value=[y[idx]]))
        features_l['x'] = Feature(float_list=FloatList(value=list(xl[idx])))
        fl.write(
            Example(features=Features(feature=features_l)).SerializeToString())

        features_f = {}
        features_f['example_id'] = Feature(
            bytes_list=BytesList(value=[str(idx).encode('utf-8')]))
        features_f['x'] = Feature(float_list=FloatList(value=list(xf[idx])))
        ff.write(
            Example(features=Features(feature=features_f)).SerializeToString())

    fl.close()
    ff.close()
