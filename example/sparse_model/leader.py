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

import tensorflow.compat.v1 as tf
import fedlearner.trainer as flt

ROLE = 'leader'

parser = flt.trainer_worker.create_argument_parser()
parser.add_argument('--batch-size', type=int, default=8,
                    help='Training batch size.')
parser.add_argument('--fid_version', type=int, default=1,
                    help="the version of fid")
args = parser.parse_args()

def input_fn(bridge, trainer_master=None):
    dataset = flt.data.DataBlockLoader(args.batch_size, ROLE,
        bridge, trainer_master).make_dataset()

    def parse_fn(example):
        feature_map = dict()
        feature_map['fids'] = tf.VarLenFeature(tf.int64)
        feature_map['example_id'] = tf.FixedLenFeature([], tf.string)
        feature_map["y"] = tf.FixedLenFeature([], tf.int64)
        features = tf.parse_example(example, features=feature_map)
        return features, dict(y=features.pop('y'))

    dataset = dataset.map(map_func=parse_fn,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset


def serving_input_receiver_fn():
    features = {}
    features['fids_indices'] = tf.placeholder(dtype=tf.int64, shape=[None],
        name='fids_indices')
    features['fids_values'] = tf.placeholder(dtype=tf.int64, shape=[None],
        name='fids_values')
    features['fids_dense_shape'] = tf.placeholder(dtype=tf.int64, shape=[None],
        name='fids_dense_shape')
    features['act1_f'] = tf.placeholder(dtype=tf.float32, shape=[None, 64],
        name='act1_f')
    return tf.estimator.export.build_raw_serving_input_receiver_fn(features)()

def model_fn(model, features, labels, mode):
    """Model Builder of wide&deep learning models
    Args:
    Returns
    """
    global_step = tf.train.get_or_create_global_step()

    flt.feature.FeatureSlot.set_default_bias_initializer(
        tf.zeros_initializer())
    flt.feature.FeatureSlot.set_default_vec_initializer(
        tf.random_uniform_initializer(-0.0078125, 0.0078125))
    flt.feature.FeatureSlot.set_default_bias_optimizer(
        tf.train.FtrlOptimizer(learning_rate=0.01))
    flt.feature.FeatureSlot.set_default_vec_optimizer(
        tf.train.AdagradOptimizer(learning_rate=0.01))

    hash_size = 101
    embed_size = 16

    if args.fid_version == 1:
        slots = [0, 1, 2, 511]
    else:
        model.set_use_fid_v2(True)
        slots = [0, 1, 2, 511, 1025]

    for slot_id in slots:
        fs = model.add_feature_slot(slot_id, hash_size)
        if slot_id < 1024:
            fc = model.add_feature_column(fs)
        else:
            fc = model.add_feature_column_v2("fc_v2_%d"%slot_id, fs)
        fc.add_vector(embed_size)

    model.freeze_slots(features)

    embed_output = model.get_vec()

    output_size = len(slots) * embed_size
    fc1_size, fc2_size = 256, 64
    w1l = tf.get_variable(
        'w1l', shape=[output_size, fc1_size], dtype=tf.float32,
        initializer=tf.random_uniform_initializer(-0.01, 0.01))
    b1l = tf.get_variable(
        'b1l', shape=[fc1_size], dtype=tf.float32,
        initializer=tf.zeros_initializer())
    w2 = tf.get_variable(
        'w2', shape=[fc1_size, fc2_size], dtype=tf.float32,
        initializer=tf.random_uniform_initializer(-0.01, 0.01))
    b2 = tf.get_variable(
        'b2', shape=[fc2_size], dtype=tf.float32,
        initializer=tf.zeros_initializer())
    w3 = tf.get_variable(
        'w3', shape=[fc2_size*2, 2], dtype=tf.float32,
        initializer=tf.random_uniform_initializer(-0.01, 0.01))

    act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(embed_output, w1l), b1l))
    act2_l = tf.nn.bias_add(tf.matmul(act1_l, w2), b2)

    if mode == tf.estimator.ModeKeys.TRAIN:
        act1_f = model.recv('act1_f', tf.float32, require_grad=True)
    else:
        act1_f = features['act1_f']
    output = tf.concat([act2_l, act1_f], axis=1)
    logits = tf.matmul(output, w3)

    if mode == tf.estimator.ModeKeys.TRAIN:
        y = labels['y']
        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(
            labels=y, logits=logits)
        loss = tf.math.reduce_mean(loss)

        logging_hook = tf.train.LoggingTensorHook(
            {"loss" : loss}, every_n_iter=10)

        optimizer = tf.train.GradientDescentOptimizer(0.1)
        train_op = model.minimize(optimizer, loss, global_step=global_step)
        return model.make_spec(mode, loss=loss, train_op=train_op,
                               training_hooks=[logging_hook])
    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode, predictions=logits)

if __name__ == '__main__':
    flt.trainer_worker.train(
        ROLE, args, input_fn,
        model_fn, serving_input_receiver_fn)
