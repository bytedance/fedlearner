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

import logging
import time
import tensorflow.compat.v1 as tf

from tensorflow.compat import as_str_any
from tensorflow.compat.v1.train import Optimizer
from tensorflow.compat.v1.estimator import ModeKeys
from tensorflow_estimator.python.estimator import model_fn as model_fn_lib

from fedlearner.common.summary_hook import SummaryHook
from fedlearner.trainer import patch  # pylint: disable=unused-import
from fedlearner.common import metrics

SYNC_PATH = '/sync/'
DATA_CHECKPOINT_INIT_VALUE = "_init_value"

class DataCheckpointSaverListener(tf.estimator.CheckpointSaverListener):
    def __init__(self, tm, appid):
        self._trainer_master = tm
        self._application_id = appid

    def begin(self):
        ckpt = tf.placeholder(tf.string, name="data_checkpoint_plhd")
        var_tmp = tf.Variable(DATA_CHECKPOINT_INIT_VALUE, \
                              name="data_checkpoint")
        self._ckpt_tensor = var_tmp.assign(ckpt)

    def before_save(self, session, global_step_value):
        logging.info('About to write a checkpoint at step %d', \
                global_step_value)
        data_checkpoint = self._trainer_master.get_data_block_checkpoint(
            self._application_id)
        #if empty block from checkpoint fetched due to exception or
        # master not ready, no need to save.
        if len(data_checkpoint) == 0:
            return
        res = session.run(self._ckpt_tensor, {"data_checkpoint_plhd:0":
                                        ",".join(data_checkpoint)})
        logging.info("data checkpoint saved result: %s", res)

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
            op = self._bridge.send_op(name, tensor)
        self._train_ops.append(op)
        self._sends.append((name, tensor, require_grad))
        if require_grad:
            return self.recv(name + '_grad', tensor.dtype)
        return None

    def recv(self, name, dtype=tf.float32, require_grad=False, shape=None):
        with tf.control_dependencies([self._example_ids]):
            tensor = self._bridge.receive_op(name, dtype)
            if shape:
                tensor = tf.ensure_shape(tensor, shape)
            else:
                logging.warning(
                    'Receiving tensor %s without checking shape. '
                    'Consider setting shape at model.recv(shape=(...)). '
                    'shape can have None dimensions '
                    'which matches to any length.', name)
        self._train_ops.append(tensor)
        self._recvs.append((name, tensor, require_grad))
        return tensor

    def minimize(self,
                 optimizer,
                 loss,
                 global_step=None,
                 var_list=None,
                 gate_gradients=Optimizer.GATE_OP,
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

    def _append_summary_hook(self, training_hooks):
        if not training_hooks:
            training_hooks = []
        summary_hook = SummaryHook.get_hook()
        if summary_hook:
            training_hooks.append(summary_hook)
        return training_hooks

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
        if mode == ModeKeys.TRAIN:
            train_op = tf.group([train_op] + self._train_ops)
            training_hooks = self._append_summary_hook(training_hooks)
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
                 model_fn,
                 bridge,
                 trainer_master,
                 role,
                 worker_rank=0,
                 application_id=None,
                 cluster_spec=None):
        self._model_fn = model_fn
        self._bridge = bridge
        self._trainer_master = trainer_master
        self._role = role
        self._worker_rank = worker_rank
        self._cluster_spec = cluster_spec
        self._application_id = application_id

    def _get_features_and_labels_from_input_fn(self, input_fn, mode):
        dataset = input_fn(self._bridge, self._trainer_master)
        features, labels = dataset.make_one_shot_iterator().get_next()
        return features, labels

    def _get_model_spec(self, features, labels, mode):
        model = FLModel(self._role, self._bridge,
                        features.get('example_id', None),
                        exporting=(mode == ModeKeys.PREDICT))
        spec = self._model_fn(model, features, labels, mode)
        return spec, model

    def _restore_datablock(self, blk_ids):
        # only chief worker restores from checkpoint.
        if self._worker_rank != 0 or blk_ids is None:
            return True
        block_id_str = as_str_any(blk_ids)
        block_ids = []
        if block_id_str != DATA_CHECKPOINT_INIT_VALUE:
            block_ids = block_id_str.split(",")
        logging.info("restore: %s", block_id_str)
        return self._trainer_master.restore_data_block_checkpoint(
            self._application_id, block_ids)

    def train(self,
              input_fn,
              checkpoint_path=None,
              save_checkpoint_steps=None,
              save_checkpoint_secs=None):

        config = tf.ConfigProto()
        config.inter_op_parallelism_threads = 16
        config.inter_op_parallelism_threads = 16
        config.experimental.share_session_state_in_clusterspec_propagation \
            = True

        if self._cluster_spec is not None:
            device_fn = tf.train.replica_device_setter(
                worker_device="/job:worker/task:%d" % self._worker_rank,
                merge_devices=True,
                cluster=self._cluster_spec)
            local_address = self._cluster_spec.job_tasks('worker')[
                self._worker_rank]
            config.rpc_options.compression_algorithm = 'gzip'
            config.rpc_options.cache_rpc_response = True
            server = tf.train.Server(tf.train.ClusterSpec(
                {'local': {
                    0: local_address
                }}),
                job_name='local',
                task_index=0,
                config=config)
            config.cluster_def.CopyFrom(self._cluster_spec.as_cluster_def())
            target = "grpc://" + local_address
        else:
            device_fn = None
            target = None

        with tf.Graph().as_default() as g:
            with tf.device(device_fn):
                features, labels = self._get_features_and_labels_from_input_fn(
                    input_fn, ModeKeys.TRAIN)
                spec, _ = self._get_model_spec(features, labels, ModeKeys.TRAIN)

            # Explicitly add a Saver
            if not tf.get_collection(tf.GraphKeys.SAVERS):
                saver = tf.train.Saver(
                    sharded=True,
                    defer_build=True,
                    save_relative_paths=True)  # Must set for portability
                tf.add_to_collection(tf.GraphKeys.SAVERS, saver)

            listener = DataCheckpointSaverListener(self._trainer_master,
                                                   self._application_id)
            saver_hook = tf.estimator.CheckpointSaverHook(
                checkpoint_path, save_secs=save_checkpoint_secs,
                save_steps=save_checkpoint_steps, listeners=[listener])
            self._bridge.connect()

            try:
                with tf.train.MonitoredTrainingSession(
                    master=target,
                    config=config,
                    is_chief=(self._worker_rank == 0),
                    chief_only_hooks=[saver_hook],
                    checkpoint_dir=checkpoint_path,
                    save_checkpoint_steps=None,
                    save_checkpoint_secs=None,
                    hooks=spec.training_hooks) as sess:
                    iter_id = 0

                    data_checkpoint_value = None
                    if hasattr(saver_hook, "data_checkpoint"):
                        data_checkpoint_value = saver_hook.data_checkpoint
                    if not self._restore_datablock(data_checkpoint_value):
                        raise ValueError("Restore data checkpoint error")

                    while not sess.should_stop():
                        self._bridge.start(iter_id)
                        logging.debug('after bridge start.')
                        start_time = time.time()
                        sess.run(spec.train_op, feed_dict={})
                        end_time = time.time()
                        metrics.emit_timer(
                            name="iter_timer",
                            value=end_time-start_time,
                            tags={})
                        logging.debug('after session run.')
                        self._bridge.commit()
                        logging.debug('after bridge commit.')
                        iter_id += 1
            finally:
                self._bridge.terminate()

        return self

    def evaluate(self,
                 input_fn,
                 checkpoint_path=None):
        if not tf.train.latest_checkpoint(checkpoint_path):
            raise ValueError(
                "Could not find trained model at %s" % checkpoint_path)

        with tf.Graph().as_default():
            features, labels = self._get_features_and_labels_from_input_fn(
                input_fn, ModeKeys.EVAL)
            spec, model = self._get_model_spec(features, labels, ModeKeys.EVAL)

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

            # Prepare the session creator.
            scaffold = tf.train.Scaffold()
            session_creator = tf.train.ChiefSessionCreator(
                scaffold=scaffold,
                checkpoint_dir=checkpoint_path)

            # Prepare hooks
            all_hooks = list(spec.evaluation_hooks) or []
            final_ops_hook = tf.train.FinalOpsHook(eval_dict)
            all_hooks.append(final_ops_hook)

            # Evaluate over dataset
            self._bridge.connect()
            try:
                with tf.train.MonitoredSession(
                    session_creator=session_creator, hooks=all_hooks) as sess:
                    if not self._restore_datablock(DATA_CHECKPOINT_INIT_VALUE):
                        raise ValueError("Restore data checkpoint error")
                    iter_id = 0
                    while not sess.should_stop():
                        self._bridge.start(iter_id)
                        logging.debug('after bridge start.')
                        start_time = time.time()
                        sess.run(eval_op)
                        end_time = time.time()
                        metrics.emit_timer(
                            name="iter_timer",
                            value=end_time-start_time,
                            tags={})
                        logging.debug('after session run.')
                        self._bridge.commit()
                        logging.debug('after bridge commit.')
                        iter_id += 1
            finally:
                self._bridge.terminate()

            # Print result
            logging.info('Metrics for iteration %d: %s',
                iter_id, _dict_to_str(final_ops_hook.final_ops_values))
            return final_ops_hook.final_ops_values

    def export_saved_model(self,
                           export_dir_base,
                           serving_input_receiver_fn,
                           checkpoint_path=None):
        with tf.Graph().as_default():
            receiver = serving_input_receiver_fn()
            spec, model = self._get_model_spec(receiver.features, None,
                                               ModeKeys.PREDICT)
            assert not model.sends, "Exported model cannot send"
            assert not model.recvs, "Exported model cannot receive"

            with tf.Session() as sess:
                saver_for_restore = tf.train.Saver(sharded=True)
                saver_for_restore.restore(
                    sess, tf.train.latest_checkpoint(checkpoint_path))
                tf.saved_model.simple_save(sess, export_dir_base,
                                           receiver.receiver_tensors,
                                           spec.predictions, None)

        return export_dir_base


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
