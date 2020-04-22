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

import io
import logging
import argparse
import numpy as np

import tensorflow.compat.v1 as tf

from fedlearner.trainer.bridge import Bridge
from fedlearner.model.tree.tree import BoostingTreeEnsamble


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description='FedLearner Tree Model Trainer.')
    parser.add_argument('role', type=str,
                        help="Role of this trainer in {'local', "
                             "'leader', 'follower'}")
    parser.add_argument('--local-addr', type=str,
                        help='Listen address of the local bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--peer-addr', type=str,
                        help='Address of peer\'s bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--application-id', type=str, default=None,
                        help='application id on distributed ' \
                             'training.')
    parser.add_argument('--data-path', type=str, default=None,
                        help='path to data block files for non-distributed ' \
                             'training. Ignored when --master-addr is set.')
    parser.add_argument('--load-model-path',
                        type=str,
                        default=None,
                        help='Path load saved models.')
    parser.add_argument('--export-path',
                        type=str,
                        default=None,
                        help='Path to save exported models.')
    parser.add_argument('--checkpoint-path',
                        type=str,
                        default=None,
                        help='Path to save model checkpoints.')
    parser.add_argument('--mode', type=str, default='train',
                        help='Running mode in train, test or eval.')
    parser.add_argument('--verbosity',
                        type=int,
                        default=1,
                        help='Controls the amount of logs to print.')
    parser.add_argument('--learning-rate',
                        type=float,
                        default=0.3,
                        help='Learning rate (shrinkage).')
    parser.add_argument('--max-iters',
                        type=int,
                        default=5,
                        help='Number of boosting iterations.')
    parser.add_argument('--max-depth',
                        type=int,
                        default=3,
                        help='Max depth of decision trees.')
    parser.add_argument('--l2-regularization',
                        type=float,
                        default=1.0,
                        help='L2 regularization parameter.')
    parser.add_argument('--max-bins',
                        type=int,
                        default=33,
                        help='Max number of histogram bins.')
    parser.add_argument('--num-parallel',
                        type=int,
                        default=1,
                        help='Number of parallel threads.')
    return parser


def train(args):
    if args.verbosity == 0:
        logging.basicConfig(level=logging.WARNING)
    elif args.verbosity == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    assert args.role in ['leader', 'follower', 'local'], \
        "role must be leader, follower, or local"
    assert args.mode in ['train', 'test', 'eval'], \
        "mode must be train, test, or eval"

    if args.data_path.endswith('.csv'):
        fin = tf.io.gfile.GFile(args.data_path, 'rb')
        data = np.loadtxt(io.BytesIO(fin.read()), delimiter=',')
        if args.mode == 'train' or args.mode == 'test':
            if args.role == 'leader' or args.role == 'local':
                X = data[:, :-1]
                y = data[:, -1]
            else:
                X = data
                y = None
        else:  # eval
            X = data
            y = None
    else:
        raise ValueError("Unsupported data type %s"%args.data_path)

    if args.role != 'local':
        bridge = Bridge(args.role, int(args.local_addr.split(':')[1]),
                        args.peer_addr, args.application_id, 0)
    else:
        bridge = None

    booster = BoostingTreeEnsamble(
        bridge,
        learning_rate=args.learning_rate,
        max_iters=args.max_iters,
        max_depth=args.max_depth,
        l2_regularization=args.l2_regularization,
        max_bins=args.max_bins,
        num_parallel=args.num_parallel)

    if args.load_model_path:
        booster.load_saved_model(args.load_model_path)

    if args.mode == 'train':
        booster.fit(X, y, args.checkpoint_path)
    elif args.mode == 'test':
        pred = booster.batch_predict(X)
        acc = sum((pred > 0.5) == y)/len(y)
        logging.info("Test accuracy: %f", acc)
    else:
        pred = booster.batch_predict(X)
        for i in pred:
            print(i)

    if args.export_path:
        booster.save_model(args.export_path)

    if bridge:
        bridge.terminate()


if __name__ == '__main__':
    train(create_argument_parser().parse_args())
