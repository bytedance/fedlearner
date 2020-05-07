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
import csv
import logging
import argparse
import traceback
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
    parser.add_argument('--mode', type=str, default='train',
                        help='Running mode in train, test or eval.')
    parser.add_argument('--data-path', type=str, default=None,
                        help='Path to data file.')
    parser.add_argument('--validation-data-path', type=str, default=None,
                        help='Path to validation data file. ' \
                             'Only used in train mode.')
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
    parser.add_argument('--output-path',
                        type=str,
                        default=None,
                        help='Path to save prediction output.')
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
    parser.add_argument('--verify-example-ids',
                        type=bool,
                        default=False,
                        help='If set to true, the first column of the '
                             'data will be treated as example ids that '
                             'must match between leader and follower')
    parser.add_argument('--use-streaming',
                        type=bool,
                        default=False,
                        help='Whether to use streaming transmit.')
    return parser


def read_csv_data(filename, has_example_ids, has_labels):
    txt_data = tf.io.gfile.GFile(filename, 'r').read()
    if has_example_ids:
        reader = csv.reader(io.StringIO(txt_data))
        lines = list(reader)
        example_ids = [i[0] for i in lines]
        data = np.asarray([line[1:] for line in lines], dtype=np.float)
    else:
        data = np.loadtxt(io.StringIO(txt_data), delimiter=',')
        example_ids = None

    if has_labels:
        X = data[:, :-1]
        y = data[:, -1]
    else:
        X = data
        y = None
    
    return X, y, example_ids


def read_data(filename, has_example_ids, has_labels):
    if filename.endswith('.csv'):
        return read_csv_data(filename, has_example_ids, has_labels)

    raise ValueError("Unsupported data type %s"%filename)


def train(args, booster):
    X, y, example_ids = read_data(
        args.data_path, args.verify_example_ids,
        args.role != 'follower')
    if args.validation_data_path:
        val_X, val_y, val_example_ids = read_data(
            args.validation_data_path, args.verify_example_ids,
            args.role != 'follower')
    booster.fit(
        X, y,
        checkpoint_path=args.checkpoint_path,
        example_ids=example_ids,
        validation_features=val_X,
        validation_labels=val_y,
        validation_example_ids=val_example_ids,
        output_path=args.output_path)


def write_predictions(filename, pred):
    fout = tf.io.gfile.GFile(filename, 'w')
    fout.write('\n'.join([str(i) for i in pred]))
    fout.close()


def test(args, booster):
    X, y, example_ids = read_data(
        args.data_path, args.verify_example_ids,
        args.role != 'follower')
    pred = booster.batch_predict(X, example_ids=example_ids)
    if args.role == 'follower':
        return

    metrics = booster.loss.metrics(pred, y)
    logging.info("Test metrics: %s", metrics)
    if args.output_path:
        write_predictions(args.output_path, pred)


def evaluate(args, booster):
    X, y, example_ids = read_data(
        args.data_path, args.verify_example_ids, False)
    pred = booster.batch_predict(X, example_ids=example_ids)

    if args.role == 'follower':
        return

    if args.output_path:
        write_predictions(args.output_path, pred)
    else:
        logging.info("Evaluation scores:")
        for i, x in enumerate(pred):
            logging.info("%d:\t%f", i, x)


def run(args):
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

    if args.role != 'local':
        bridge = Bridge(args.role, int(args.local_addr.split(':')[1]),
                        args.peer_addr, args.application_id, 0,
                        streaming_mode=args.use_streaming)
    else:
        bridge = None

    try:
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
            train(args, booster)
        elif args.mode == 'test':
            test(args, booster)
        else:  # args.mode == 'eval'
            evaluate(args, booster)

        if args.export_path:
            booster.save_model(args.export_path)
    except Exception as e:
        logging.fatal(
            'Exception raised during training: %s',
            traceback.format_exc())
        raise e
    finally:
        if bridge:
            bridge.terminate()


if __name__ == '__main__':
    run(create_argument_parser().parse_args())
