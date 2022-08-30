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
    dataset = flt.data.DataBlockLoader(256, 'follower', bridge,
                                       trainer_master)\
        .make_dataset(compression_type='GZIP')
    def parse_fn(example):
        feature_map = {
            "example_id": tf.FixedLenFeature([], tf.string),
            "y": tf.FixedLenFeature([], tf.int64)
        }
        features = tf.parse_example(example, features=feature_map)
        labels = {'y': features.pop('y')}
        return features, labels
    dataset = dataset.map(map_func=parse_fn,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset


def serving_input_receiver_fn():
    feature_map = {
        "example_id": tf.FixedLenFeature([], tf.string),
    }
    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.parse_example(record_batch, features=feature_map)
    return tf.estimator.export.ServingInputReceiver(features,
                                                    {'examples': record_batch})


def model_fn(model, features, labels, mode):
    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode=mode,
                               predictions=features)

    y = labels['y']
    if mode == tf.estimator.ModeKeys.TRAIN:
        logits = model.recv('logits', tf.float32, require_grad=True)
    else:
        logits = model.recv('logits', tf.float32, require_grad=False)
    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,
                                                          logits=logits)
    loss = tf.math.reduce_mean(loss)
    correct = tf.nn.in_top_k(predictions=logits, targets=y, k=1)
    acc = tf.reduce_mean(input_tensor=tf.cast(correct, tf.float32))
    model.send('loss', loss, require_grad=False)
    model.send('accuracy', acc, require_grad=False)
    if mode == tf.estimator.ModeKeys.EVAL:
        return model.make_spec(mode=mode, loss=loss)

    logging.info("training")
    optimizer = tf.train.GradientDescentOptimizer(0.1)
    train_op = model.minimize(
        optimizer, loss,
        global_step=tf.train.get_or_create_global_step())
    return model.make_spec(mode,
                           loss=loss,
                           train_op=train_op)


def main(args):
    flt.trainer_worker.train(
        'follower', args, input_fn,
        model_fn, serving_input_receiver_fn)

#if __name__ == '__main__':
#    main()
