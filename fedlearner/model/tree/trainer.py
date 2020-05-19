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
import csv
import queue
import logging
import argparse
import traceback
import numpy as np

import tensorflow.compat.v1 as tf

from fedlearner.trainer.bridge import Bridge
from fedlearner.model.tree.tree import BoostingTreeEnsamble
from fedlearner.trainer.trainer_master_client import LocalTrainerMasterClient
from fedlearner.trainer.trainer_master_client import DataBlockInfo


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
    parser.add_argument('--worker-rank', type=int, default=0,
                        help='rank of the current worker')
    parser.add_argument('--num-workers', type=int, default=1,
                        help='total number of workers')
    parser.add_argument('--mode', type=str, default='train',
                        help='Running mode in train, test or eval.')
    parser.add_argument('--data-path', type=str, default=None,
                        help='Path to data file.')
    parser.add_argument('--validation-data-path', type=str, default=None,
                        help='Path to validation data file. ' \
                             'Only used in train mode.')
    parser.add_argument('--no-data', type=bool, default=False,
                        help='Run prediction without data.')
    parser.add_argument('--file-ext', type=str, default='.csv',
                        help='File extension to use')
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
    parser.add_argument('--ignore-fields',
                        type=str,
                        default='',
                        help='Ignore data fields by name')
    parser.add_argument('--use-streaming',
                        type=bool,
                        default=False,
                        help='Whether to use streaming transmit.')

    return parser

def extract_field(field_names, field_name, required):
    if field_name in field_names:
        return field_names.index(field_name), []

    assert not required, \
        "Data must contain %s field"%field_name
    return None, None

def read_csv_data(filename, require_example_ids, require_labels,
                  ignore_fields):
    logging.debug('Reading csv file from %s', filename)
    fin = tf.io.gfile.GFile(filename, 'r')
    reader = csv.reader(fin)
    field_names = next(reader)

    example_id_idx, example_ids = extract_field(
        field_names, 'example_id', require_example_ids)
    label_idx, labels = extract_field(
        field_names, 'label', require_labels)

    ignore_fields = set(ignore_fields.strip().split(','))
    ignore_fields.update(['example_id', 'raw_id', 'label'])
    data_columns = [
        (i, name) for i, name in enumerate(field_names) \
            if name not in ignore_fields]
    data_columns.sort(key=lambda x: x[1])
    data = []

    for line in reader:
        if example_id_idx is not None:
            example_ids.append(line[example_id_idx])
        if label_idx is not None:
            labels.append(float(line[label_idx]))
        data.append([float(line[i]) for i, _ in data_columns])

    data = np.asarray(data, dtype=np.float)
    if labels is not None:
        labels = np.asarray(labels, dtype=np.float)

    fin.close()
    return data, labels, example_ids


def train(args, booster):
    X, y, example_ids = read_csv_data(
        args.data_path, args.verify_example_ids,
        args.role != 'follower', args.ignore_fields)

    if args.validation_data_path:
        val_X, val_y, val_example_ids = read_csv_data(
            args.validation_data_path, args.verify_example_ids,
            args.role != 'follower', args.ignore_fields)
    else:
        val_X = val_y = val_example_ids = None

    if args.output_path:
        tf.io.gfile.makedirs(os.path.dirname(args.output_path))

    booster.fit(
        X, y,
        checkpoint_path=args.checkpoint_path,
        example_ids=example_ids,
        validation_features=val_X,
        validation_labels=val_y,
        validation_example_ids=val_example_ids,
        output_path=args.output_path)


def write_predictions(filename, pred, example_ids=None):
    logging.debug("Writing predictions to %s", filename)
    fout = tf.io.gfile.GFile(filename, 'w')
    if example_ids is not None:
        header = 'example_id,prediction'
        lines = zip(example_ids, pred)
    else:
        header = 'prediction'
        lines = zip(pred)

    fout.write(header+'\n')
    for line in lines:
        fout.write(','.join([str(i) for i in line]) + '\n')

    fout.close()

def test_one_file(args, booster, data_file, output_file):
    if data_file is None:
        X = y = example_ids = None
    else:
        X, y, example_ids = read_csv_data(
            data_file, args.verify_example_ids,
            False, args.ignore_fields)

    pred = booster.batch_predict(X, example_ids=example_ids)

    if y is not None:
        metrics = booster.loss.metrics(pred, y)
    else:
        metrics = {}
    logging.info("Test metrics: %s", metrics)

    if output_file:
        tf.io.gfile.makedirs(os.path.dirname(output_file))
        write_predictions(output_file, pred, example_ids)


class DataBlockLoader(object):
    def __init__(self, role, bridge, data_path, ext,
                 worker_rank=0, num_workers=1):
        self._role = role
        self._bridge = bridge
        self._num_workers = num_workers
        self._worker_rank = worker_rank

        self._tm_role = 'follower' if role == 'leader' else 'leader'

        if data_path:
            files = None
            if not tf.io.gfile.isdir(data_path):
                files = [os.path.basename(data_path)]
                data_path = os.path.dirname(data_path)
            self._trainer_master = LocalTrainerMasterClient(
                self._tm_role, data_path, files=files, ext=ext)
        else:
            self._trainer_master = None

        self._count = 0
        if self._role == 'leader':
            self._block_queue = queue.Queue()
            self._bridge.register_data_block_handler(self._data_block_handler)
            self._bridge.start(self._bridge.new_iter_id())
            self._bridge.send(
                self._bridge.current_iter_id, 'barrier', np.asarray([1]))
            self._bridge.commit()
        elif self._role == 'follower':
            self._bridge.start(self._bridge.new_iter_id())
            self._bridge.receive(self._bridge.current_iter_id, 'barrier')
            self._bridge.commit()

    def _data_block_handler(self, msg):
        logging.debug('DataBlock: recv "%s" at %d', msg.block_id, msg.count)
        assert self._count == msg.count
        if not msg.block_id:
            block = None
        elif self._trainer_master is not None:
            block = self._trainer_master.request_data_block(msg.block_id)
            if block is None:
                raise ValueError("Block %s not found" % msg.block_id)
        else:
            block = DataBlockInfo(msg.block_id, None)
        self._count += 1
        self._block_queue.put(block)

    def _request_data_block(self):
        for _ in range(self._worker_rank):
            self._trainer_master.request_data_block()
        block = self._trainer_master.request_data_block()
        for _ in range(self._num_workers - self._worker_rank - 1):
            self._trainer_master.request_data_block()
        return block

    def get_next_block(self):
        if self._role == 'local':
            return self._request_data_block()

        if self._tm_role == 'leader':
            while True:
                block = self._request_data_block()
                if block is not None:
                    try:
                        self._bridge.load_data_block(self._count,
                                                     block.block_id)
                    except Exception as e:  # pylint: disable=broad-except
                        logging.error('load data block %s with error: %s',
                                      block.block_id, repr(e))
                        continue
                else:
                    self._bridge.load_data_block(self._count, '')
                break
            self._count += 1
        else:
            block = self._block_queue.get()
        return block


def test(args, bridge, booster):
    if not args.no_data:
        assert args.data_path, "Data path must not be empty"
    else:
        assert not args.data_path and args.role == 'leader'

    data_loader = DataBlockLoader(
        args.role, bridge, args.data_path, args.file_ext,
        args.worker_rank, args.num_workers)

    while True:
        data_block = data_loader.get_next_block()
        if data_block is None:
            break
        if args.output_path:
            output_file = os.path.join(
                args.output_path, data_block.block_id) + '.output'
        else:
            output_file = None
        test_one_file(
            args, booster, data_block.data_path, output_file)


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
        else:  # args.mode == 'test, eval'
            test(args, bridge, booster)

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
