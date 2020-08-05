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
# pylint: disable=no-else-return, inconsistent-return-statements

import logging
import tensorflow.compat.v1 as tf
import fedlearner.trainer as flt

ROLE = 'follower'
parser = flt.trainer_worker.create_argument_parser()
parser.add_argument('--batch-size', type=int, default=256,
                    help='Training batch size.')
parser.add_argument('--fid_version', type=int, default=1,
                    help="the version of fid")
args = parser.parse_args()

def input_fn(bridge, trainer_master=None):
    dataset = flt.data.DataBlockLoader(args.batch_size, ROLE,
        bridge, trainer_master).make_dataset()
    def parse_fn(example):
        feature_map = dict()
        feature_map = {"fids": tf.VarLenFeature(tf.int64)}
        feature_map["example_id"] = tf.FixedLenFeature([], tf.string)
        features = tf.parse_example(example, features=feature_map)
        return features, dict(y=tf.constant(0))
    dataset = dataset.map(map_func=parse_fn,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset

def serving_input_receiver_fn():
    feature_map = {}
    feature_map['fids_indices'] = tf.placeholder(dtype=tf.int64, shape=[None],
        name='fids_indices')
    feature_map['fids_values'] = tf.placeholder(dtype=tf.int64, shape=[None],
        name='fids_values')
    feature_map['fids_dense_shape'] = tf.placeholder(dtype=tf.int64,
        shape=[None], name='fids_dense_shape')
    return tf.estimator.export.ServingInputReceiver(
        feature_map, feature_map)

def model_fn(model, features, labels, mode):
    global_step = tf.train.get_or_create_global_step()

    flt.feature.FeatureSlot.set_default_bias_initializer(
        tf.zeros_initializer())
    flt.feature.FeatureSlot.set_default_vec_initializer(
        tf.random_uniform_initializer(-0.0078125, 0.0078125))
    flt.feature.FeatureSlot.set_default_bias_optimizer(
        tf.train.FtrlOptimizer(learning_rate=0.01))
    flt.feature.FeatureSlot.set_default_vec_optimizer(
        tf.train.AdagradOptimizer(learning_rate=0.01))

    if args.fid_version == 1:
        slots = [512, 1023]
    else:
        model.set_use_fid_v2(True)
        slots = [512, 1023, 32767]
    hash_size = 101
    embed_size = 16
    for slot_id in slots:
        fs = model.add_feature_slot(slot_id, hash_size)
        fc = model.add_feature_column(fs)
        fc.add_vector(embed_size)

    model.freeze_slots(features)

    embed_output = model.get_vec()

    output_size = len(slots) * embed_size
    fc1_size = 64
    w1f = tf.get_variable(
        'w1f', shape=[output_size, fc1_size], dtype=tf.float32,
        initializer=tf.random_uniform_initializer(-0.01, 0.01))
    b1f = tf.get_variable(
        'b1f', shape=[fc1_size], dtype=tf.float32,
        initializer=tf.zeros_initializer())

    act1_f = tf.nn.relu(tf.nn.bias_add(tf.matmul(embed_output, w1f), b1f))

    if mode == tf.estimator.ModeKeys.TRAIN:
        gact1_f = model.send('act1_f', act1_f, require_grad=True)
        optimizer = tf.train.GradientDescentOptimizer(0.1)
        train_op = model.minimize(
            optimizer, act1_f, grad_loss=gact1_f, global_step=global_step)
        return model.make_spec(mode, loss=tf.math.reduce_mean(act1_f),
                               train_op=train_op,)
    elif mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode, predictions={'act1_f': act1_f})


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    flt.trainer_worker.train(
        ROLE, args, input_fn,
        model_fn, serving_input_receiver_fn)
