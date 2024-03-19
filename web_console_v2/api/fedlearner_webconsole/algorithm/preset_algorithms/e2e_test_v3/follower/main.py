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
import numpy as np
import tensorflow.compat.v1 as tf
import fedlearner.trainer as flt
from config import *
from fedlearner.trainer.trainer_worker import StepLossAucMetricsHook

ROLE = 'follower'

parser = flt.trainer_worker.create_argument_parser()
parser.add_argument('--batch-size', type=int, default=10, help='Training batch size.')
args = parser.parse_args()


class ResultWriter:

    def __init__(self):
        self.result = {}

    def update_result(self, raw_id, pred):
        raw_id = raw_id.numpy()
        pred = pred.numpy()
        for i in range(len(raw_id)):
            self.result[raw_id[i]] = pred[i]

    def write_result(self, filename):
        raw_id = np.array(list(self.result.keys())).reshape(-1)
        pred = np.array([self.result[i] for i in raw_id]).reshape(-1)
        with tf.gfile.Open(filename, 'w') as f:
            np.savetxt(f, np.dstack((raw_id, pred))[0], '%s,%f', header='raw_id,pred')
        logging.info(f'[write_result]output result to {filename}')


result_writer = ResultWriter()


def input_fn(bridge, trainer_master):
    dataset = flt.data.DataBlockLoader(args.batch_size, ROLE, bridge, trainer_master).make_dataset()

    def parse_fn(example):
        feature_map = dict()
        feature_map['example_id'] = tf.FixedLenFeature([], tf.string)
        feature_map['raw_id'] = tf.FixedLenFeature([], tf.string)
        for name in follower_feature_names:
            feature_map[name] = tf.FixedLenFeature([], tf.float32, default_value=0.0)
        features = tf.parse_example(example, features=feature_map)
        return features, dict(y=tf.constant(0))

    dataset = dataset.map(map_func=parse_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    return dataset


def serving_input_receiver_fn():
    feature_map = {
        'example_id': tf.FixedLenFeature([], tf.string),
        'raw_id': tf.FixedLenFeature([], tf.string),
    }
    for name in follower_feature_names:
        feature_map[name] = tf.FixedLenFeature([], tf.float32, default_value=0.0)
    record_batch = tf.placeholder(dtype=tf.string, name='examples')
    features = tf.parse_example(record_batch, features=feature_map)
    features['act1_f'] = tf.placeholder(dtype=tf.float32, name='act1_f')
    receiver_tensors = {'examples': record_batch, 'act1_f': features['act1_f']}
    return tf.estimator.export.ServingInputReceiver(features, receiver_tensors)


def model_fn(model, features, labels, mode):
    logging.info('model_fn: mode %s', mode)
    x = [tf.expand_dims(features[name], axis=-1) for name in follower_feature_names]
    x = tf.concat(x, axis=-1)

    w1f = tf.get_variable('w1l',
                          shape=[len(follower_feature_names), len(leader_label_name)],
                          dtype=tf.float32,
                          initializer=tf.random_uniform_initializer(-0.01, 0.01))
    b1f = tf.get_variable('b1l', shape=[len(leader_label_name)], dtype=tf.float32, initializer=tf.zeros_initializer())

    act1_f = tf.nn.bias_add(tf.matmul(x, w1f), b1f)

    if mode == tf.estimator.ModeKeys.PREDICT:
        return model.make_spec(mode=mode, predictions=act1_f)

    if mode == tf.estimator.ModeKeys.TRAIN:
        gact1_f = model.send('act1_f', act1_f, require_grad=True)
    elif mode == tf.estimator.ModeKeys.EVAL:
        model.send('act1_f', act1_f, require_grad=False)

    pred = model.recv('pred', tf.float32, require_grad=False)
    raw_id = features['raw_id']
    update_result_op = tf.py_function(result_writer.update_result, [raw_id, pred], [], 'update')
    with tf.control_dependencies([update_result_op]):
        auc = model.recv('auc', tf.float32, require_grad=False)
        loss = model.recv('loss', tf.float32, require_grad=False)

    logging_hook = tf.train.LoggingTensorHook({
        'auc': auc,
        'loss': loss,
    }, every_n_iter=10)
    step_metric_hook = StepLossAucMetricsHook(loss_tensor=loss, auc_tensor=auc, every_n_iter=1)

    global_step = tf.train.get_or_create_global_step()
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.GradientDescentOptimizer(0.1)
        train_op = model.minimize(optimizer, act1_f, grad_loss=gact1_f, global_step=global_step)
        return model.make_spec(mode,
                               loss=tf.math.reduce_mean(act1_f),
                               train_op=train_op,
                               training_hooks=[logging_hook, step_metric_hook])
    if mode == tf.estimator.ModeKeys.EVAL:
        fake_loss = tf.reduce_mean(act1_f)
        return model.make_spec(mode=mode, loss=fake_loss, evaluation_hooks=[logging_hook, step_metric_hook])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    outputs_path = os.path.join(os.environ['OUTPUT_BASE_DIR'], 'outputs')
    tf.gfile.MakeDirs(outputs_path)
    flt.trainer_worker.train(ROLE, args, input_fn, model_fn, serving_input_receiver_fn)
    if args.worker:
        result_writer.write_result(os.path.join(outputs_path, f'worker-{str(args.worker_rank)}.csv'))
