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
import tensorflow.compat.v1 as tf

from fedlearner.trainer.bridge import Bridge
from fedlearner.trainer.estimator import FLEstimator
from fedlearner.trainer.sparse_estimator import SparseFLEstimator
from fedlearner.trainer.trainer_master_client import LocalTrainerMasterClient
from fedlearner.trainer.trainer_master_client import TrainerMasterClient


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
    parser.add_argument('--save-checkpoint-steps',
                        type=int,
                        default=1000,
                        help='Number of steps between checkpoints.')
    parser.add_argument('--sparse-estimator', type=bool, default=False,
                        help='Whether using sparse estimator.')

    return parser

def train(role, args, input_fn, model_fn, serving_input_receiver_fn):
    bridge = Bridge(role, int(args.local_addr.split(':')[1]), args.peer_addr)

    if args.cluster_spec:
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
    elif args.data_path:
        trainer_master = LocalTrainerMasterClient(role, args.data_path)
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
    elif args.data_source:
        if args.start_time is None or args.end_time is None:
            raise ValueError(
                "data source must be set with start-date and end-date")
        trainer_master = LocalTrainerMasterClient(role,
                                                  args.data_source,
                                                  start_time=args.start_time,
                                                  end_time=args.end_time)
        cluster_spec = None
    else:
        raise ValueError("Either --master-addr or --data-path must be set")

    if args.sparse_estimator:
        estimator = SparseFLEstimator(
            model_fn, bridge, trainer_master, role,
            worker_rank=args.worker_rank,
            cluster_spec=cluster_spec)
    else:
        estimator = FLEstimator(
            model_fn, bridge, trainer_master, role,
            worker_rank=args.worker_rank,
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
