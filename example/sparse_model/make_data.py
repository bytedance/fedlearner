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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import random
import shutil
import numpy as np
import tensorflow.compat.v1 as tf

from tensorflow.core.example.example_pb2 import Example
from tensorflow.core.example.feature_pb2 import Features, Feature, \
                                                Int64List, BytesList

current_dir = os.path.dirname(__file__)
shutil.rmtree(os.path.join(current_dir, 'data'), ignore_errors=True)
os.makedirs(os.path.join(current_dir, 'data/leader'))
os.makedirs(os.path.join(current_dir, 'data/follower'))

FEATURE_BITS = 53

LEADER_SLOT_RANGE = (0, 512)
FOLLOWER_SLOT_RANGE = (512, 1024)

N = 10
chunk_size = 10000

def _make_fid(slot_id, hash_value):
    return int(np.int64(np.uint64((hash_value & ((1 << FEATURE_BITS) - 1)) | \
                                  (slot_id << FEATURE_BITS))))

def _make_random_fid(slot_id):
    return _make_fid(slot_id, int(np.int64(random.getrandbits(54))))

def _fake_sample(slot_range):
    fids = []
    for slot in slot_range:
        fids.append(_make_random_fid(slot))
    return fids

for i in range(N):
    filename_l = os.path.join(current_dir, 'data/leader/%02d.tfrecord'%i)
    filename_f = os.path.join(current_dir, 'data/follower/%02d.tfrecord'%i)
    fl = tf.io.TFRecordWriter(filename_l)
    ff = tf.io.TFRecordWriter(filename_f)

    for j in range(chunk_size):
        idx = i*chunk_size + j
        features_l = {}
        features_l['example_id'] = \
            Feature(bytes_list=BytesList(value=[str(idx)]))
        features_l['y'] = \
            Feature(int64_list=Int64List(value=[random.randint(0, 1)]))
        features_l['fids'] = \
            Feature(int64_list=Int64List(value=_fake_sample(LEADER_SLOT_RANGE)))
        fl.write(
            Example(features=Features(feature=features_l)).SerializeToString())

        features_f = {}
        features_f['example_id'] = \
            Feature(bytes_list=BytesList(value=[str(idx)]))
        features_f['fids'] = \
            Feature(int64_list=Int64List(
                value=_fake_sample(FOLLOWER_SLOT_RANGE)))
        ff.write(
            Example(features=Features(feature=features_f)).SerializeToString())

    fl.close()
    ff.close()
