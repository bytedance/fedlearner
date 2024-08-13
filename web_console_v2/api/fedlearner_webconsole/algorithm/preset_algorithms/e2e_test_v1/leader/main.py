# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import logging
import tensorflow.compat.v1 as tf
import fedlearner.trainer as flt
from config import *
from fedlearner.trainer.trainer_worker import StepLossAucMetricsHook

ROLE = 'leader'

parser = flt.trainer_worker.create_argument_parser()
parser.add_argument('--batch-size', type=int, default=100, help='Training batch size.')
args = parser.parse_args()


def input_fn(bridge, trainer_master):
    dataset = flt.data.DataBlockLoader(args.batch_size, ROLE, bridge, trainer_master).make_dataset()

    def parse_fn(example):
        feature_map = dict()
        feature_map['example_id'] = tf.FixedLenFeature([], tf.string)
        feature_map['raw_id'] = tf.FixedLenFeature([], tf.string)
        for name in leader_feature_names:
            feature_map[name] = tf.FixedLenFeature([], tf.float32, default_value=0.0)
        label_map = {}
        for name in leader_label_name:
            label_map[name] = tf.FixedLenFeature([], tf.float32, default_value=0.0)
        features = tf.parse_example(example, features=feature_map)
        labels = tf.parse_example(example, features=label_map)
        return features, labels

    dataset = dataset.map(map_func=parse_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset


def serving_input_receiver_fn():
    feature_map = {
        "example_id": tf.FixedLenFeature([], tf.string),
        "raw_id": tf.FixedLenFeature([], tf.string),
    }
    for name in leader_feature_names:
        feature_map[name] = tf.FixedLenFeature([], tf.float32, default_value=0.0)
    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.parse_example(record_batch, features=feature_map)
    features['act1_f'] = tf.placeholder(dtype=tf.float32, name='act1_f')
    receiver_tensors = {'examples': record_batch, 'act1_f': features['act1_f']}
    return tf.estimator.export.ServingInputReceiver(features, receiver_tensors)


def model_fn(model, features, labels, mode):
    logging.info('model_fn: mode %s', mode)
    x = [tf.expand_dims(features[name], axis=-1) for name in leader_feature_names]
    x = tf.concat(x, axis=-1)

    w1l = tf.get_variable('w1l',
                          shape=[len(leader_feature_names), len(leader_label_name)],
                          dtype=tf.float32,
                          initializer=tf.random_uniform_initializer(-0.01, 0.01))
    b1l = tf.get_variable('b1l', shape=[len(leader_label_name)], dtype=tf.float32, initializer=tf.zeros_initializer())

    act1_l = tf.nn.bias_add(tf.matmul(x, w1l), b1l)
    if mode == tf.estimator.ModeKeys.TRAIN:
        act1_f = model.recv('act1_f', tf.float32, require_grad=True)
    elif mode == tf.estimator.ModeKeys.EVAL:
        act1_f = model.recv('act1_f', tf.float32, require_grad=False)
    else:
        act1_f = features['act1_f']
    logits = act1_l + act1_f
    pred = tf.math.sigmoid(logits)

    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode=mode, predictions=pred)

    y = [tf.expand_dims(labels[name], axis=-1) for name in leader_label_name]
    y = tf.concat(y, axis=-1)

    loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=y, logits=logits)
    _, auc = tf.metrics.auc(labels=y, predictions=pred)
    #correct = tf.nn.in_top_k(predictions=logits, targets=y, k=1)
    #acc = tf.reduce_mean(input_tensor=tf.cast(correct, tf.float32))
    logging_hook = tf.train.LoggingTensorHook(
        {
            #    'acc': acc,
            'auc': auc,
            'loss': loss,
        },
        every_n_iter=10)
    step_metric_hook = StepLossAucMetricsHook(loss_tensor=loss, auc_tensor=auc)
    #model.send('acc', acc, require_grad=False)
    model.send('auc', auc, require_grad=False)
    model.send('loss', loss, require_grad=False)

    global_step = tf.train.get_or_create_global_step()
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.AdamOptimizer(1e-4)
        train_op = model.minimize(optimizer, loss, global_step=global_step)
        return model.make_spec(mode=mode, loss=loss, train_op=train_op, training_hooks=[logging_hook, step_metric_hook])

    if mode == tf.estimator.ModeKeys.EVAL:
        loss_pair = tf.metrics.mean(loss)
        return model.make_spec(mode=mode,
                               loss=loss,
                               eval_metric_ops={'loss': loss_pair},
                               evaluation_hooks=[logging_hook, step_metric_hook])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    flt.trainer_worker.train(ROLE, args, input_fn, model_fn, serving_input_receiver_fn)
