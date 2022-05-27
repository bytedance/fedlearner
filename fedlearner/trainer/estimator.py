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
# pylint: disable=protected-access

import time

import tensorflow.compat.v1 as tf
from tensorflow.python.estimator.util import parse_input_fn_result #pylint: disable=no-name-in-module

from tensorflow_estimator.python.estimator import model_fn as model_fn_lib
from fedlearner.common import fl_logging


class FLModel(object):
    def __init__(self, role, bridge, example_ids, exporting=False):
        self._role = role
        self._bridge = bridge
        self._example_ids = example_ids
        self._exporting = exporting

        self._train_ops = []
        self._recvs = []
        self._sends = []
        self._outputs = []

    @property
    def train_ops(self):
        return self._train_ops

    @property
    def sends(self):
        return [(n, t) for n, t, _ in self._sends]

    @property
    def recvs(self):
        return [(n, t) for n, t, _ in self._recvs]

    def verify_example_ids(self):
        tensor = tf.strings.to_hash_bucket_fast(self._example_ids, 2**31 - 1)
        if self._role == 'leader':
            self.send('_verify_example_ids', tensor)
        else:
            recv_tensor = self.recv('_verify_example_ids', tensor.dtype)
            op = tf.assert_equal(tensor, recv_tensor)
            self._train_ops.append(op)

    def send(self, name, tensor, require_grad=False):
        with tf.control_dependencies([self._example_ids]):
            send_op = self._bridge.send_op(name, tensor)
        self._sends.append((name, tensor, require_grad))
        if require_grad:
            with tf.control_dependencies([send_op]):
                return self.recv(name + '_grad', tensor.dtype)
        else:
            self._train_ops.append(send_op)

        return None

    def recv(self, name, dtype=tf.float32, require_grad=False, shape=None):
        with tf.control_dependencies([self._example_ids]):
            receive_op = self._bridge.receive_op(name, dtype)
        if shape:
            receive_op = tf.ensure_shape(receive_op, shape)
        else:
            fl_logging.warning(
                'Receiving tensor %s without checking shape. '
                'Consider setting shape at model.recv(shape=(...)). '
                'shape can have None dimensions '
                'which matches to any length.', name)
        self._train_ops.append(receive_op)
        self._recvs.append((name, receive_op, require_grad))
        return receive_op

    def minimize(self,
                 optimizer,
                 loss,
                 global_step=None,
                 var_list=None,
                 gate_gradients=tf.train.Optimizer.GATE_OP,
                 aggregation_method=None,
                 colocate_gradients_with_ops=False,
                 name=None,
                 grad_loss=None):
        recv_grads = [i for i in self._recvs if i[2]]

        if var_list is None:
            var_list = \
                tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES) + \
                tf.get_collection(tf.GraphKeys.TRAINABLE_RESOURCE_VARIABLES)
        var_list = [v for _, v, _ in recv_grads] + var_list

        grads_and_vars = optimizer.compute_gradients(
            loss,
            var_list=var_list,
            gate_gradients=gate_gradients,
            aggregation_method=aggregation_method,
            colocate_gradients_with_ops=colocate_gradients_with_ops,
            grad_loss=grad_loss)

        send_grads = grads_and_vars[:len(recv_grads)]
        for (n, _, _), (grad, _) in zip(recv_grads, send_grads):
            if grad is not None:
                self.send(n + '_grad', grad)

        if grads_and_vars[len(recv_grads):]:
            train_op = optimizer.apply_gradients(
                grads_and_vars[len(recv_grads):],
                global_step=global_step,
                name=name)
        else:
            train_op = tf.no_op()

        return train_op

    def make_spec(self,
                  mode,
                  predictions=None,
                  loss=None,
                  train_op=None,
                  eval_metric_ops=None,
                  training_chief_hooks=None,
                  training_hooks=None,
                  evaluation_hooks=None,
                  prediction_hooks=None):
        if isinstance(predictions, tf.Tensor):
            predictions = {'output': predictions}
        if mode == tf.estimator.ModeKeys.TRAIN:
            train_op = tf.group([train_op] + self._train_ops)
        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions,
            loss=loss,
            train_op=train_op,
            eval_metric_ops=eval_metric_ops,
            training_chief_hooks=training_chief_hooks,
            training_hooks=training_hooks,
            evaluation_hooks=evaluation_hooks,
            prediction_hooks=prediction_hooks)


class FLEstimator(object):
    def __init__(self,
                 cluster_server,
                 trainer_master,
                 bridge,
                 role,
                 model_fn,
                 is_chief=False):
        self._cluster_server = cluster_server
        self._bridge = bridge
        self._role = role
        self._model_fn = model_fn
        self._trainer_master = trainer_master
        self._is_chief = is_chief
        self._input_hooks = []

    def _get_features_and_labels_from_input_fn(self, input_fn, mode):
        features, labels, input_hooks = parse_input_fn_result(
            input_fn(self._bridge, self._trainer_master))
        self._input_hooks = input_hooks
        return features, labels

    def _get_model_spec(self, features, labels, mode):
        model = FLModel(self._role, self._bridge,
                        features.get("example_id", None),
                        exporting=(mode == tf.estimator.ModeKeys.PREDICT))
        spec = self._model_fn(model, features, labels, mode)
        return spec, model

    def train(self, input_fn):

        with tf.Graph().as_default() as g, \
            g.device(self._cluster_server.device_setter):

            features, labels = self._get_features_and_labels_from_input_fn(
                input_fn, tf.estimator.ModeKeys.TRAIN)
            spec, _ = self._get_model_spec(
                features, labels, tf.estimator.ModeKeys.TRAIN)

            hooks = []
            # user define chief hook
            if spec.training_chief_hooks and self._is_chief:
                hooks.extend(spec.training_chief_hooks)

            if spec.training_hooks:
                hooks.extend(spec.training_hooks)

            if self._input_hooks:
                hooks.extend(self._input_hooks)

            session_creator = tf.train.WorkerSessionCreator(
                master=self._cluster_server.target,
                config=self._cluster_server.cluster_config)

            self._bridge.connect()
            with tf.train.MonitoredSession(
                session_creator=session_creator, hooks=hooks) as sess:
                while not sess.should_stop():
                    start_time = time.time()
                    self._bridge.start()
                    sess.run(spec.train_op, feed_dict={})
                    self._bridge.commit()
                    use_time = time.time() - start_time
                    fl_logging.debug("after session run. time: %f sec",
                                     use_time)
            self._bridge.terminate()

        return self

    def evaluate(self, input_fn):

        with tf.Graph().as_default() as g, \
            g.device(self._cluster_server.device_setter):

            features, labels = self._get_features_and_labels_from_input_fn(
                input_fn, tf.estimator.ModeKeys.EVAL)
            spec, model = self._get_model_spec(
                features, labels, tf.estimator.ModeKeys.EVAL)

            # Track the average loss in default
            eval_metric_ops = spec.eval_metric_ops or {}
            if model_fn_lib.LOSS_METRIC_KEY not in eval_metric_ops:
                loss_metric = tf.metrics.mean(spec.loss)
                eval_metric_ops[model_fn_lib.LOSS_METRIC_KEY] = loss_metric

            # Create the real eval op
            update_ops, eval_dict = _extract_metric_update_ops(eval_metric_ops)
            update_ops.extend(model._train_ops)
            eval_op = tf.group(*update_ops)

            # Also track the global step
            if tf.GraphKeys.GLOBAL_STEP in eval_dict:
                raise ValueError(
                    'Metric with name `global_step` is not allowed, because '
                    'Estimator already defines a default metric with the '
                    'same name.')
            eval_dict[tf.GraphKeys.GLOBAL_STEP] = \
                tf.train.get_or_create_global_step()

            # Prepare hooks
            all_hooks = []
            if spec.evaluation_hooks:
                all_hooks.extend(spec.evaluation_hooks)
            final_ops_hook = tf.train.FinalOpsHook(eval_dict)
            all_hooks.append(final_ops_hook)

            session_creator = tf.train.WorkerSessionCreator(
                master=self._cluster_server.target,
                config=self._cluster_server.cluster_config)
            # Evaluate over dataset
            self._bridge.connect()
            with tf.train.MonitoredSession(
                session_creator=session_creator, hooks=all_hooks) as sess:
                while not sess.should_stop():
                    start_time = time.time()
                    self._bridge.start()
                    sess.run(eval_op)
                    self._bridge.commit()
                    use_time = time.time() - start_time
                    fl_logging.debug("after session run. time: %f sec",
                                     use_time)
            self._bridge.terminate()

            # Print result
            fl_logging.info('Metrics for evaluate: %s',
                _dict_to_str(final_ops_hook.final_ops_values))

        return self


def _extract_metric_update_ops(eval_dict):
    """Separate update operations from metric value operations."""
    update_ops = []
    value_ops = {}
    # Sort metrics lexicographically so graph is identical every time.
    for name in sorted(eval_dict.keys()):
        metric_tensor, update_op = eval_dict[name]
        value_ops[name] = metric_tensor
        update_ops.append(update_op)
    return update_ops, value_ops


def _dict_to_str(dictionary):
    """Get a `str` representation of a `dict`.

    Args:
        dictionary: The `dict` to be represented as `str`.

    Returns:
        A `str` representing the `dictionary`.
    """
    return ', '.join('%s = %s' % (k, v)
                     for k, v in sorted(dictionary.items())
                     if not isinstance(v, bytes))
