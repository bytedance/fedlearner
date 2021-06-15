
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
import socket
import threading
import shutil
import unittest
import numpy as np
import tensorflow.compat.v1 as tf
import fedlearner.trainer as flt

run_step = 2
batch_size = 256

def union_shuffle(a, b):
    assert len(a) == len(a)
    p = np.random.permutation(len(a))
    return a[p], b[p]

(x, y), _ = tf.keras.datasets.mnist.load_data()
x, y = union_shuffle(x, y)

total_features = x.reshape(x.shape[0], -1).astype(np.float32) / 255.0
total_labels = y.astype(np.int64)

drop_count = total_features.shape[0] % (run_step * batch_size)
if drop_count > 0:
    total_features = total_features[:-drop_count]
    total_labels = total_labels[:-drop_count]

total_leader_features = total_features[:, :total_features.shape[1]//2]
total_follower_features = total_features[:, total_features.shape[1]//2:]

step_leader_features = np.split(total_leader_features, run_step)
step_follower_features = np.split(total_follower_features, run_step)
step_labels = np.split(total_labels, run_step)

class HookContext():
    def __init__(self):
        self._saved_value = dict()
    
    @property
    def saved_value(self):
        return self._saved_value

    def create_logging_and_save_tensor_hook(self,
                                            tensors,
                                            every_n_iter=None,
                                            every_n_secs=None,
                                            at_end=False,
                                            formatter=None):
        return LoggingAndSaveTensorHook(tensors,
                                        every_n_iter,
                                        every_n_secs,
                                        at_end,
                                        formatter,
                                        self._saved_value)



class LoggingAndSaveTensorHook(tf.train.LoggingTensorHook):
    def __init__(self,
                 tensors,
                 every_n_iter=None,
                 every_n_secs=None,
                 at_end=False,
                 formatter=None,
                 saved_value=None):
        super(LoggingAndSaveTensorHook, self).__init__(tensors,
                                                       every_n_iter,
                                                       every_n_secs,
                                                       at_end,
                                                       formatter)
        self._saved_value = saved_value if saved_value is not None else dict()

    def _log_tensors(self, tensor_values):
        for tag in self._tag_order:
            if tag not in self._saved_value:
                self._saved_value[tag] = []
            self._saved_value[tag].append(tensor_values[tag])
        super(LoggingAndSaveTensorHook, self)._log_tensors(tensor_values)


def create_input_fn(features, labels):
    def input_fn(bridge, master):
        def mapfunc(x, y):
            feature = {
                "x": x,
                "example_id": tf.constant(0)
            }
            return feature, y

        return tf.data.Dataset.from_tensor_slices((features, labels)) \
                .map(mapfunc) \
                .batch(batch_size, drop_remainder=True)
    return input_fn

def create_leader_model_fn(hook_context):
    def leader_model_fn(model, features, labels, mode):
        x, y = features["x"], labels

        w1 = tf.get_variable("w1",
                             shape=[x.shape[1], 32],
                             dtype=tf.float32,
                             initializer=tf.random_uniform_initializer(seed=0))

        b1 = tf.get_variable("b1",
                             shape=[32],
                             dtype=tf.float32,
                             initializer=tf.zeros_initializer())

        w2 = tf.get_variable("w2",
                             shape=[32 * 2, 10],
                             dtype=tf.float32,
                             initializer=tf.random_uniform_initializer(seed=0))

        b2 = tf.get_variable("b2",
                             shape=[10],
                             dtype=tf.float32,
                             initializer=tf.zeros_initializer())

        act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(x, w1), b1))
        if mode == tf.estimator.ModeKeys.TRAIN:
            act1_f = model.recv("act1_f", tf.float32, require_grad=True)
        else:
            act1_f = model.recv("act1_f", tf.float32, require_grad=False)
        act1 = tf.concat([act1_l, act1_f], axis=1)
        logits = tf.nn.bias_add(tf.matmul(act1, w2), b2)

        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,
                                                              logits=logits)
        loss = tf.math.reduce_mean(loss)

        if mode == tf.estimator.ModeKeys.TRAIN:
            optimizer = tf.train.AdamOptimizer()
            train_op = model.minimize(
                optimizer, loss, global_step=tf.train.get_or_create_global_step())
            correct = tf.nn.in_top_k(predictions=logits, targets=y, k=1)
            acc = tf.reduce_mean(input_tensor=tf.cast(correct, tf.float32))
            logging_hook = hook_context.create_logging_and_save_tensor_hook(
                {"loss" : loss, "acc" : acc}, every_n_iter=1)
            return model.make_spec(
                mode=mode, loss=loss, train_op=train_op,
                training_hooks=[logging_hook])
        else:
            classes = tf.argmax(logits, axis=1)
            acc_pair = tf.metrics.accuracy(y, classes)
            return model.make_spec(
                mode=mode, loss=loss, eval_metric_ops={'accuracy': acc_pair})

    return leader_model_fn


def follower_model_fn(model, features, labels, mode):
    x, _ = features["x"], labels

    w1 = tf.get_variable("w1",
                         shape=[x.shape[1], 32],
                         dtype=tf.float32,
                         initializer=tf.random_uniform_initializer(seed=0))

    b1 = tf.get_variable("b1",
                         shape=[32],
                         dtype=tf.float32,
                         initializer=tf.zeros_initializer())

    act1_f = tf.nn.relu(tf.nn.bias_add(tf.matmul(x, w1), b1))
    gact1_f = model.send("act1_f", act1_f, require_grad=True)
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.AdamOptimizer()
        train_op = model.minimize(
            optimizer,
            act1_f,
            grad_loss=gact1_f,
            global_step=tf.train.get_or_create_global_step())
        return model.make_spec(mode,
                               loss=tf.math.reduce_mean(act1_f),
                               train_op=train_op)

    else:
        model.send("act1_f", act1_f, require_grad=False)
        fake_loss = tf.reduce_mean(act1_f)
        return model.make_spec(mode=mode, loss=fake_loss)


class _CreateParamaterServer():
    def __init__(self):
        self._server = tf.train.Server.create_local_server()

    @property
    def address(self):
        return self._server.target[7:]

    def stop(self):
        del(self._server)
        

class TestStepTrain(unittest.TestCase):
    def setUp(self):
        self._current_dir = os.path.dirname(__file__)
        self._model_dir = os.path.join(self._current_dir, 'tmp_model')
        shutil.rmtree(self._model_dir, ignore_errors=True)
        self._leader_output = os.path.join(self._model_dir, 'leader')
        self._follower_output = os.path.join(self._model_dir, 'follower')
        self._leader_bridge_addr = _get_free_tcp_address()
        self._follower_bridge_addr = _get_free_tcp_address()

    def tearDown(self):
        shutil.rmtree(self._model_dir, ignore_errors=True)

    def _run_train(self,
                   hook_context,
                   leader_features,
                   follower_features,
                   labels,
                   leader_checkpoint_path=None,
                   follower_checkpoint_path=None,
                   save_checkpoint_step=100):
        """ train without checkpoint"""
        parser = flt.trainer_worker.create_argument_parser()
        # leader
        leader_ps1 = _CreateParamaterServer()
        leader_raw_args = (
            "--local-addr", self._leader_bridge_addr,
            "--peer-addr", self._follower_bridge_addr,
            "--data-path", self._current_dir, # noused
            "--ps-addrs", ",".join([leader_ps1.address]),
            "--loglevel", "debug",
            )
        if leader_checkpoint_path:
            leader_raw_args += \
                ("--checkpoint-path", leader_checkpoint_path)
            leader_raw_args += \
                ("--save-checkpoint-steps", str(save_checkpoint_step))
        leader_trainer = threading.Thread(
            target=flt.trainer_worker.train,
            args=("leader",
                  parser.parse_args(leader_raw_args),
                  create_input_fn(leader_features, labels),
                  create_leader_model_fn(hook_context),
                  None)
        )

        # follower 
        follower_ps1 = _CreateParamaterServer()
        follower_raw_args = (
            "--local-addr", self._follower_bridge_addr,
            "--peer-addr", self._leader_bridge_addr,
            "--data-path", self._current_dir, # noused
            "--ps-addrs", ",".join([follower_ps1.address]),
            "--loglevel", "debug",
            )
        if follower_checkpoint_path:
            follower_raw_args += \
                ("--checkpoint-path",follower_checkpoint_path)
            follower_raw_args += \
                ("--save-checkpoint-steps", str(save_checkpoint_step))
        follower_trainer = threading.Thread(
            target=flt.trainer_worker.train,
            args=("follower",
                  parser.parse_args(follower_raw_args),
                  create_input_fn(follower_features, labels),
                  follower_model_fn,
                  None)
        )
        leader_trainer.start()
        follower_trainer.start()
        leader_trainer.join()
        follower_trainer.join()
        leader_ps1.stop()
        follower_ps1.stop()

    def test_train(self):
        # run all in one step
        total_hook_context = HookContext()
        self._run_train(total_hook_context,
                        total_leader_features,
                        total_follower_features,
                        total_labels)
        print(total_hook_context.saved_value)

        # run step by step
        step_hook_context = HookContext()
        leader_checkpoint_path = \
            os.path.join(self._leader_output, "checkpoints")
        follower_checkpoint_path = \
            os.path.join(self._follower_output, "checkpoints")
        for i in range(run_step):
            leader_features = step_leader_features[i]
            follower_features = step_follower_features[i]
            labels = step_labels[i]
            self._run_train(step_hook_context,
                            leader_features,
                            follower_features,
                            labels,
                            leader_checkpoint_path=leader_checkpoint_path,
                            follower_checkpoint_path=follower_checkpoint_path,
                            save_checkpoint_step=200)
        print(step_hook_context.saved_value)

        # check
        assert len(total_hook_context.saved_value) == \
            len(step_hook_context.saved_value)
        for tag in total_hook_context.saved_value:
            assert tag in step_hook_context.saved_value
            assert len(total_hook_context.saved_value[tag]) == \
                 len(step_hook_context.saved_value[tag])
            print("%stag: %s%s"%("*"*32, tag, "*"*32))
            print("%15s%20s%20s%20s"%("index(step)", "total", "part", "diff"))
            step = 0
            count = len(step_hook_context.saved_value[tag]) // run_step
            for i, v1 in enumerate(total_hook_context.saved_value[tag]):
                if i % count == 0:
                    step += 1
                v2 = step_hook_context.saved_value[tag][i]
                print("%15s%20f%20f%20f"% \
                    (str(i)+"("+str(step)+")", v1, v2, v1-v2))
                assert v1 == v2
            print("%s"%("*"*75))
            print()

def _get_free_tcp_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    host, port = s.getsockname()
    s.close()
    return "%s:%d"%(host, port)

if __name__ == "__main__":
    unittest.main()
