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

import os
import tensorflow.compat.v1 as tf
import fedlearner.trainer as flt

ROLE = 'leader'

parser = flt.trainer_worker.create_argument_parser()
parser.add_argument('--batch-size', type=int, default=256,
                    help='Training batch size.')

args = parser.parse_args()

with open("custom_env") as f:
    line = f.readline()
    while line:
        kv = line.split("=")
        if len(kv) == 2:
            os.environ[kv[0]] = kv[1].strip()
        line = f.readline(); 

print(os.environ)

def input_fn(bridge, trainer_master):
    dataset = flt.data.DataBlockLoader(args.batch_size, ROLE,
        bridge, trainer_master).make_dataset()

    def parse_fn(example):
        feature_map = dict()
        feature_map['example_id'] = tf.FixedLenFeature([], tf.string)
        feature_map['x'] = tf.FixedLenFeature([28 * 28 // 2], tf.float32)
        feature_map['y'] = tf.FixedLenFeature([], tf.int64)
        features = tf.parse_example(example, features=feature_map)
        return features, dict(y=features.pop('y'))

    dataset = dataset.map(map_func=parse_fn,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset


def serving_input_receiver_fn():
    feature_map = {
        "example_id": tf.FixedLenFeature([], tf.string),
        "x": tf.FixedLenFeature([28 * 28 // 2], tf.float32),
    }
    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.parse_example(record_batch, features=feature_map)
    features['act1_f'] = tf.placeholder(dtype=tf.float32, name='act1_f')
    receiver_tensors = {'examples': record_batch, 'act1_f': features['act1_f']}
    return tf.estimator.export.ServingInputReceiver(features, receiver_tensors)


def model_fn(model, features, labels, mode):
    x = features['x']

    w1l = tf.get_variable('w1l',
                          shape=[28 * 28 // 2, 128],
                          dtype=tf.float32,
                          initializer=tf.random_uniform_initializer(
                              -0.01, 0.01))
    b1l = tf.get_variable('b1l',
                          shape=[128],
                          dtype=tf.float32,
                          initializer=tf.zeros_initializer())
    w2 = tf.get_variable('w2',
                         shape=[128 * 2, 10],
                         dtype=tf.float32,
                         initializer=tf.random_uniform_initializer(
                             -0.01, 0.01))
    b2 = tf.get_variable('b2',
                         shape=[10],
                         dtype=tf.float32,
                         initializer=tf.zeros_initializer())

    act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(x, w1l), b1l))
    if mode == tf.estimator.ModeKeys.TRAIN:
        act1_f = model.recv('act1_f', tf.float32, require_grad=True)
    elif mode == tf.estimator.ModeKeys.EVAL:
        act1_f = model.recv('act1_f', tf.float32, require_grad=False)
    else:
        act1_f = features['act1_f']
    act1 = tf.concat([act1_l, act1_f], axis=1)
    logits = tf.nn.bias_add(tf.matmul(act1, w2), b2)

    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode=mode, predictions=logits)

    y = labels['y']
    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,
                                                          logits=logits)
    loss = tf.math.reduce_mean(loss)

    if mode == tf.estimator.ModeKeys.EVAL:
        classes = tf.argmax(logits, axis=1)
        acc_pair = tf.metrics.accuracy(y, classes)
        return model.make_spec(
            mode=mode, loss=loss, eval_metric_ops={'accuracy': acc_pair})

    # mode == tf.estimator.ModeKeys.TRAIN
    optimizer = tf.train.GradientDescentOptimizer(0.1)
    train_op = model.minimize(
        optimizer, loss, global_step=tf.train.get_or_create_global_step())
    correct = tf.nn.in_top_k(predictions=logits, targets=y, k=1)
    acc = tf.reduce_mean(input_tensor=tf.cast(correct, tf.float32))
    logging_hook = tf.train.LoggingTensorHook(
        {"loss" : loss, "acc" : acc}, every_n_iter=10)
    return model.make_spec(
        mode=mode, loss=loss, train_op=train_op,
        training_hooks=[logging_hook])


if __name__ == '__main__':
    flt.trainer_worker.train(
        ROLE, args, input_fn,
        model_fn, serving_input_receiver_fn)
