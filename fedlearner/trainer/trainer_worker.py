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

import argparse
import json
import logging
import os

try:
    import tensorflow.compat.v1 as tf
except ImportError:
    import tensorflow as tf

from fedlearner.common import metrics
from fedlearner.common.summary_hook import SummaryHook
from fedlearner.trainer.bridge import Bridge
from fedlearner.trainer.estimator import FLEstimator
from fedlearner.trainer.sparse_estimator import SparseFLEstimator
from fedlearner.trainer.trainer_master_client import LocalTrainerMasterClient
from fedlearner.trainer.trainer_master_client import TrainerMasterClient


class StepMetricsHook(tf.train.SessionRunHook):
    def __init__(self, tensor_dict=None, every_n_iter=5, tags_dict=None):
        if tensor_dict is None:
            tensor_dict = {}
        if tags_dict is None:
            tags_dict = {}
        self._tensor_names = list(tensor_dict.keys())
        self._tag_names = list(tags_dict.keys())
        # merge
        self._tensor_dict = {**tensor_dict, **tags_dict}
        self._every_n_iter = every_n_iter
        self._iter = 0

    def before_run(self, run_context):
        return tf.estimator.SessionRunArgs(self._tensor_dict)

    def after_run(self, run_context, run_value):
        self._iter += 1
        if self._iter % self._every_n_iter == 0:
            result = run_value.results
            tags = {}
            for tag in self._tag_names:
                if tag in result:
                    tags[tag] = result[tag]
            for name in self._tensor_names:
                if name in result:
                    metrics.emit_store(name=name, value=result[name], tags=tags)


class StepLossAucMetricsHook(StepMetricsHook):
    def __init__(self, loss_tensor, auc_tensor, every_n_iter=5,
                 event_time_tensor=None):

        tensor_dict = {"loss": loss_tensor,
                       "auc": auc_tensor}
        tags_dict = {}
        if event_time_tensor is not None:
            tags_dict["event_time"] = event_time_tensor
        super(StepLossAucMetricsHook, self).__init__(
            tensor_dict, every_n_iter, tags_dict
        )


def create_argument_parser():
    parser = argparse.ArgumentParser(description='FedLearner Trainer.')
    parser.add_argument('--local-addr', type=str,
                        help='Listen address of the local bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--peer-addr', type=str,
                        help='Address of peer\'s bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--cluster-spec', type=str,
                        help='ClusterSpec description for master/ps/worker, '\
                            'in json format')
    parser.add_argument('--worker-rank',
                        type=int,
                        default=0,
                        help='the rank of this worker.')
    parser.add_argument('--ps-addrs', type=str, default=None,
                        help='Comma-separated list of parameter server ' \
                             'addresses in [IP]:[PORT] format. ' \
                             'value for this argument must be identical ' \
                             'for all workers.')
    parser.add_argument('--data-source', type=str, default=None,
                        help='path to data source for distributed file system' \
                             'training. Ignored when --master-addr is set.')
    parser.add_argument('--data-path', type=str, default=None,
                        help='path to data block files for non-distributed ' \
                             'training. Ignored when --master-addr is set.')
    parser.add_argument('--application-id', type=str, default=None,
                        help='application id on distributed ' \
                             'training.')
    parser.add_argument('--start-time', type=str, default=None,
                        help='start-time on data source ' \
                             'training. Ignored when --master-addr is set.')
    parser.add_argument('--end-time', type=str, default=None,
                        help='end-time on data source ' \
                             'training. Ignored when --master-addr is set.')
    parser.add_argument('--master-addr', type=str, default=None,
                        help='Address of trainer master, ' \
                             'in [IP]:[PORT] format. ' \
                             'Use local master for testing if set to None.')
    parser.add_argument('--tf-addr', type=str, default=None,
                        help='Address of tensorflow server, ' \
                             'in localhost:[PORT] format')
    parser.add_argument('--export-path',
                        type=str,
                        default=None,
                        help='Path to save exported models.')
    parser.add_argument('--checkpoint-path',
                        type=str,
                        default=None,
                        help='Path to save and load model checkpoints.')
    parser.add_argument('--load-checkpoint-filename',
                        type=str,
                        default=None,
                        help='filename to load model checkpoints, ' \
                             'Relative path to checkpoint-path')
    parser.add_argument('--load-checkpoint-filename-with-path',
                        type=str,
                        default=None,
                        help='filename with path to load model checkpoints')
    parser.add_argument('--save-checkpoint-steps',
                        type=int,
                        default=None,
                        help='Number of steps between checkpoints.')
    parser.add_argument('--sparse-estimator',
                        type=bool,
                        default=False,
                        help='Whether using sparse estimator.')
    parser.add_argument('--mode',
                        type=str,
                        default='train',
                        help='Train or eval.')
    parser.add_argument('--epoch_num',
                        type=int,
                        default=1,
                        help='number of epoch for training')
    parser.add_argument('--save-checkpoint-secs',
                        type=int,
                        default=None,
                        help='Number of secs between checkpoints.')
    parser.add_argument('--summary-path',
                        type=str,
                        default=None,
                        help='Path to save summary files used by tensorboard.')
    parser.add_argument('--summary-save-steps',
                        type=int,
                        default=None,
                        help='Number of steps to save summary files.')
    parser.add_argument('--verbosity',
                        type=int,
                        default=1,
                        help='Logging level.')

    return parser


def train(role, args, input_fn, model_fn, serving_input_receiver_fn):
    logging.basicConfig(
        format="%(asctime)-15s [%(filename)s:%(lineno)d] " \
               "%(levelname)s : %(message)s")
    if args.verbosity == 0:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbosity > 1:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.application_id:
        bridge = Bridge(role, int(args.local_addr.split(':')[1]),
                        args.peer_addr, args.application_id, args.worker_rank)
    else:
        bridge = Bridge(role, int(args.local_addr.split(':')[1]),
                        args.peer_addr)

    if args.data_path:
        trainer_master = LocalTrainerMasterClient(role,
                                                  args.data_path,
                                                  epoch_num=args.epoch_num)
        if args.ps_addrs is not None:
            ps_addrs = args.ps_addrs.split(",")
            cluster_spec = tf.train.ClusterSpec({
                'ps': ps_addrs,
                'worker': {
                    args.worker_rank: args.tf_addr
                }
            })
        else:
            cluster_spec = None
    elif args.cluster_spec:
        cluster_spec = json.loads(args.cluster_spec)
        assert 'clusterSpec' in cluster_spec, \
            "cluster_spec do not meet legal format"
        assert 'Master' in cluster_spec['clusterSpec'],\
            "cluster_spec must include Master"
        assert isinstance(cluster_spec['clusterSpec']['Master'], list), \
            "Master must be list"
        assert 'Worker' in cluster_spec['clusterSpec'],\
            "cluster_spec must include Worker"
        assert isinstance(cluster_spec['clusterSpec']['Worker'], list), \
            "Worker must be list"
        trainer_master = TrainerMasterClient(
            cluster_spec['clusterSpec']['Master'][0], role, args.worker_rank)
        cluster_spec = tf.train.ClusterSpec({
            'ps':
            cluster_spec['clusterSpec']['PS'],
            'worker': {
                args.worker_rank: args.tf_addr
            }
        })
    elif args.master_addr:
        assert args.tf_addr is not None, \
            "--tf-addr must be set when master_addr is set."
        trainer_master = TrainerMasterClient(args.master_addr, role,
                                             args.worker_rank)
        ps_addrs = args.ps_addrs.split(",")
        cluster_spec = tf.train.ClusterSpec({
            'ps': ps_addrs,
            'worker': {
                args.worker_rank: args.tf_addr
            }
        })
    elif args.data_source:
        if args.start_time is None or args.end_time is None:
            raise ValueError(
                "data source must be set with start-date and end-date")
        trainer_master = LocalTrainerMasterClient(role,
                                                  args.data_source,
                                                  start_time=args.start_time,
                                                  end_time=args.end_time,
                                                  epoch_num=args.epoch_num)
        cluster_spec = None
    else:
        raise ValueError("Either --master-addr or --data-path must be set")

    if args.summary_path:
        SummaryHook.summary_path = args.summary_path
        SummaryHook.worker_rank = args.worker_rank
        SummaryHook.role = role
    if args.summary_save_steps:
        SummaryHook.save_steps = args.summary_save_steps

    if args.sparse_estimator:
        estimator = SparseFLEstimator(model_fn,
                                      bridge,
                                      trainer_master,
                                      role,
                                      worker_rank=args.worker_rank,
                                      application_id=args.application_id,
                                      cluster_spec=cluster_spec)
    else:
        estimator = FLEstimator(model_fn,
                                bridge,
                                trainer_master,
                                role,
                                worker_rank=args.worker_rank,
                                application_id=args.application_id,
                                cluster_spec=cluster_spec)

    load_checkpoint_filename_with_path = args.load_checkpoint_filename_with_path
    if not load_checkpoint_filename_with_path:
        load_checkpoint_filename_with_path = \
            _get_load_checkpoint_filename_with_path(
                args.checkpoint_path, args.load_checkpoint_filename)
    if load_checkpoint_filename_with_path:
        if not tf.train.checkpoint_exists(load_checkpoint_filename_with_path):
            raise RuntimeError("not a valid checkpoint file: %s"\
                %load_checkpoint_filename_with_path)

    run_mode = args.mode.lower()
    if run_mode == 'train':
        estimator.train(input_fn,
                        checkpoint_path=args.checkpoint_path,
                        load_checkpoint_filename_with_path= \
                            load_checkpoint_filename_with_path,
                        save_checkpoint_steps=args.save_checkpoint_steps,
                        save_checkpoint_secs=args.save_checkpoint_secs)
        if args.export_path and args.worker_rank == 0:
            export_path = '%s/%d' % (args.export_path, bridge.terminated_at)
            estimator.export_saved_model(export_path,
                                         serving_input_receiver_fn,
                                         checkpoint_path=args.checkpoint_path)
            fsuccess = tf.io.gfile.GFile('%s/_SUCCESS' % export_path, 'w')
            fsuccess.write('%d' % bridge.terminated_at)
            fsuccess.close()

    elif run_mode == 'eval':
        if not load_checkpoint_filename_with_path:
            raise RuntimeError("can not find any checkpoint for eval")
        estimator.evaluate(
            input_fn,
            load_checkpoint_filename_with_path= \
                load_checkpoint_filename_with_path)
    else:
        raise ValueError('Allowed values are: --mode=train|eval')

def _get_load_checkpoint_filename_with_path(
    checkpoint_path, checkpoint_filename):
    if not (checkpoint_path or checkpoint_filename):
        return None
    if checkpoint_filename:
        if not checkpoint_path:
            raise ValueError("checkpoint_path is required "
                "when provide checkpoint_filename")
        return os.path.join(checkpoint_path, checkpoint_filename)

    return tf.train.latest_checkpoint(checkpoint_path)
