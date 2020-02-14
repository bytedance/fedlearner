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

import tensorflow.compat.v1 as tf

from fedlearner.trainer.bridge import Bridge
from fedlearner.trainer.estimator import FLEstimator
from fedlearner.trainer.trainer_master import LocalTrainerMasterClient
from fedlearner.trainer.trainer_master import TrainerMasterClient


def create_argument_parser():
    parser = argparse.ArgumentParser(description='FedLearner Trainer.')
    parser.add_argument('--local-addr', type=str, required=True,
                        help='Listen address of the local bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--peer-addr', type=str, required=True,
                        help='Address of peer\'s bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--worker-rank', type=int, default=0,
                         help='the rank of this worker.')
    parser.add_argument('--ps-addrs', type=str, default=None,
                        help='Comma-separated list of parameter server ' \
                             'addresses in [IP]:[PORT] format. ' \
                             'value for this argument must be identical ' \
                             'for all workers.')
    parser.add_argument('--data-path', type=str, default=None,
                        help='path to data block files for non-distributed ' \
                             'training. Ignored when --master-addr is set.')
    parser.add_argument('--master-addr', type=str, default=None,
                        help='Address of trainer master, ' \
                             'in [IP]:[PORT] format. ' \
                             'Use local master for testing if set to None.')
    parser.add_argument('--tf-addr', type=str, default=None,
                        help='Address of tensorflow server, ' \
                             'in localhost:[PORT] format')
    parser.add_argument('--export-path', type=str, default=None,
                        help='Path to save exported models.')
    parser.add_argument('--checkpoint-path', type=str, default=None,
                        help='Path to save and load model checkpoints.')
    parser.add_argument('--save-checkpoint-steps', type=int, default=None,
                        help='Number of steps between checkpoints.')

    return parser


def train(role, args, input_fn, model_fn, serving_input_receiver_fn):
    bridge = Bridge(role, int(args.local_addr.split(':')[1]),
                               args.peer_addr)

    if args.master_addr:
        assert args.tf_addr is not None, \
            "--tf-addr must be set when master_addr is set."
        trainer_master = TrainerMasterClient(
            args.master_addr, role, args.worker_rank)
        cluster_spec = tf.train.ClusterSpec({
            'ps': args.ps_addrs,
            'worker': {args.worker_rank: args.tf_addr}})
    elif args.data_path:
        trainer_master = LocalTrainerMasterClient(role, args.data_path)
        cluster_spec = None
    else:
        raise ValueError("Either --master-addr or --data-path must be set")

    estimator = FLEstimator(
        model_fn, bridge, trainer_master, role, worker_rank=args.worker_rank,
        cluster_spec=cluster_spec)
    if args.checkpoint_path:
        estimator.train(input_fn,
                        checkpoint_path=args.checkpoint_path,
                        save_checkpoint_steps=args.save_checkpoint_steps)
    else:
        estimator.train(input_fn)

    if args.export_path:
        estimator.export_saved_model(args.export_path,
                                    serving_input_receiver_fn,
                                    checkpoint_path=args.checkpoint_path)
