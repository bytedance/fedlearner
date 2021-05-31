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


def input_fn(bridge, trainer_master):
    dataset = flt.data.DataBlockLoader(256, 'leader', bridge, trainer_master)\
        .make_dataset(compression_type='GZIP')
    def parse_fn(example):
        feature_map = {
            "example_id": tf.FixedLenFeature([], tf.string),
            "x": tf.FixedLenFeature([28 * 28], tf.float32),
            "y": tf.FixedLenFeature([], tf.int64)
        }
        features = tf.parse_example(example, features=feature_map)
        labels = {'y': features.pop('y')}
        print("Leader worker input_fn    ", labels)
        return features, labels
    return dataset.map(map_func=parse_fn,
            num_parallel_calls=tf.data.experimental.AUTOTUNE)


def serving_input_receiver_fn():
    feature_map = {
        "example_id": tf.FixedLenFeature([], tf.string),
        "x": tf.FixedLenFeature([28 * 28], tf.float32),
    }
    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.parse_example(record_batch, features=feature_map)
    features['act1_f'] = tf.placeholder(dtype=tf.float32, name='act1_f')
    receiver_tensors = {'examples': record_batch, 'act1_f': features['act1_f']}
    return tf.estimator.export.ServingInputReceiver(features, receiver_tensors)


def model_def(features):
    x = features['x']

    w1l = tf.get_variable('w1l',
                          shape=[28 * 28, 256],
                          dtype=tf.float32,
                          initializer=tf.random_uniform_initializer(
                              -0.01, 0.01))
    b1l = tf.get_variable('b1l',
                          shape=[256],
                          dtype=tf.float32,
                          initializer=tf.zeros_initializer())
    w2 = tf.get_variable('w2',
                         shape=[256, 10],
                         dtype=tf.float32,
                         initializer=tf.random_uniform_initializer(
                             -0.01, 0.01))
    b2 = tf.get_variable('b2',
                         shape=[10],
                         dtype=tf.float32,
                         initializer=tf.zeros_initializer())

    act1 = tf.nn.relu(tf.nn.bias_add(tf.matmul(x, w1l), b1l))
    logits = tf.nn.bias_add(tf.matmul(act1, w2), b2)
    return logits

def remote_model_fn(model, features, labels, mode):
    logits = model_def(features)

    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode=mode, predictions=logits)

    y = labels['y']
    if mode == tf.estimator.ModeKeys.EVAL:
        classes = tf.argmax(logits, axis=1)
        acc_pair = tf.metrics.accuracy(y, classes)
        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,
                                                              logits=logits)
        loss = tf.math.reduce_mean(loss)
        return model.make_spec(
            mode=mode, loss=loss, eval_metric_ops={'accuracy': acc_pair})
    # mode == tf.estimator.ModeKeys.TRAIN
    optimizer = tf.train.GradientDescentOptimizer(0.1)
    logits_grad = model.send('logits', logits, require_grad=True)
    loss = model.recv('loss', tf.float32, require_grad=False)
    acc = model.recv('accuracy', tf.float32, require_grad=False)
    train_op = model.minimize(
        optimizer, logits,
        grad_loss=logits_grad,
        global_step=tf.train.get_or_create_global_step())
    logging_hook = tf.train.LoggingTensorHook(
        {"loss" : loss, "acc" : acc}, every_n_iter=10)
    return model.make_spec(
        mode=mode, loss=loss, train_op=train_op,
        training_hooks=[logging_hook])


def local_model_fn(model, features, labels, mode):
    logits = model_def(features)

    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode=mode, predictions=logits)

    y = labels['y']
    if mode == tf.estimator.ModeKeys.EVAL:
        classes = tf.argmax(logits, axis=1)
        acc_pair = tf.metrics.accuracy(y, classes)
        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,
                                                              logits=logits)
        loss = tf.math.reduce_mean(loss)
        return model.make_spec(
            mode=mode, loss=loss, eval_metric_ops={'accuracy': acc_pair})

    # mode == tf.estimator.ModeKeys.TRAIN
    optimizer = tf.train.GradientDescentOptimizer(0.1)
    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,
                                                          logits=logits)
    loss = tf.math.reduce_mean(loss)

    train_op = model.minimize(
        optimizer, loss, global_step=tf.train.get_or_create_global_step())
    correct = tf.nn.in_top_k(predictions=logits, targets=y, k=1)
    acc = tf.reduce_mean(input_tensor=tf.cast(correct, tf.float32))
    logging_hook = tf.train.LoggingTensorHook(
        {"loss": loss, "acc": acc}, every_n_iter=10)
    return model.make_spec(
        mode=mode, loss=loss, train_op=train_op,
        training_hooks=[logging_hook])


def main(args):
    logging.getLogger().setLevel(level=logging.DEBUG)
    if args.local_worker:
        flt.trainer_worker.train(
            'leader', args, input_fn,
            local_model_fn, serving_input_receiver_fn)
    else:
        flt.trainer_worker.train(
            'leader', args, input_fn,
            remote_model_fn, serving_input_receiver_fn)

#if __name__ == '__main__':
#    parser = flt.trainer_worker.create_argument_parser()
#    args = parser.parse_args()
#    main(args)
