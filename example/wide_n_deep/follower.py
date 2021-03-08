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
args = parser.parse_args()


def input_fn(bridge, trainer_master=None):
    dataset = flt.data.DataBlockLoader(
        args.batch_size, ROLE, bridge, trainer_master).make_dataset()

    def parse_fn(example):
        feature_map = {"x_{0}".format(i): tf.VarLenFeature(
            tf.int64) for i in range(512)}
        feature_map["example_id"] = tf.FixedLenFeature([], tf.string)
        features = tf.parse_example(example, features=feature_map)
        labels = {}
        return features, labels

    dataset = dataset.map(map_func=parse_fn,
                          num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset

def serving_input_receiver_fn():
    feature_map = {"x_{0}".format(i): tf.VarLenFeature(
        tf.int64) for i in range(512)}
    feature_map["example_id"] = tf.FixedLenFeature([], tf.string)

    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.parse_example(record_batch, features=feature_map)
    return tf.estimator.export.ServingInputReceiver(
        features, {'examples': record_batch})


def model_fn(model, features, labels, mode):
    global_step = tf.train.get_or_create_global_step()

    x = [features['x_{0}'.format(i)] for i in range(512)]

    num_slot = 512
    fid_size, embed_size = 101, 16
    embeddings = [
        tf.get_variable('slot_emb{0}'.format(i),
                        shape=[fid_size, embed_size], dtype=tf.float32,
                        initializer=tf.random_uniform_initializer(-0.01, 0.01))
                        for i in range(num_slot)]
    embed_output = tf.concat(
        [
            tf.nn.embedding_lookup_sparse(
                embeddings[i], x[i], sp_weights=None, combiner='mean')
            for i in range(num_slot)],
        axis=1)

    output_size = num_slot * embed_size
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
                               train_op=train_op)

    if mode == tf.estimator.ModeKeys.EVAL:
        model.send('act1_f', act1_f, require_grad=False)
        fake_loss = tf.reduce_mean(act1_f)
        return model.make_spec(mode=mode, loss=fake_loss)

    # mode == tf.estimator.ModeKeys.PREDICT:
    return model.make_spec(mode, predictions={'act1_f': act1_f})


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
        format="[%(levelname)s] %(asctime)s: %(message)s "
            "in %(pathname)s:%(lineno)d")
    flt.trainer_worker.train(
        ROLE, args, input_fn,
        model_fn, serving_input_receiver_fn)
