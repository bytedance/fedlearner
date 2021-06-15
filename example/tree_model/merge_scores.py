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
import logging
import argparse
import itertools
import tensorflow.compat.v1 as tf
from fedlearner.model.tree.trainer import DataBlockLoader


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description='Merge prediction scores with example_id.')

    parser.add_argument('--worker-rank', type=int, default=0,
                        help='rank of the current worker')
    parser.add_argument('--num-workers', type=int, default=1,
                        help='total number of workers')

    parser.add_argument('--left-data-path', type=str,
                        help="left side data path")
    parser.add_argument('--left-file-ext', type=str,
                        help="left side data file extension")
    parser.add_argument('--left-select-fields', type=str,
                        help="left side selected field names")

    parser.add_argument('--right-data-path', type=str,
                        help="right side data path")
    parser.add_argument('--right-file-ext', type=str,
                        help="right side data file extension")
    parser.add_argument('--right-select-fields', type=str,
                        help="right side selected field names")

    parser.add_argument('--output-path', type=str,
                        help="Output path")

    return parser


def merge(args, left_file, right_file, out_file):
    logging.info("Merging %s and %s into %s", left_file, right_file, out_file)

    left_reader = csv.DictReader(tf.io.gfile.GFile(left_file, 'r'))
    right_reader = csv.DictReader(tf.io.gfile.GFile(right_file, 'r'))
    left_fields = args.left_select_fields.strip().split(',')
    right_fields = args.right_select_fields.strip().split(',')
    for i in left_fields:
        assert i in left_reader.fieldnames, \
            "Field %s missing in left file %s"%(i, left_file)
    for i in right_fields:
        assert i in right_reader.fieldnames, \
            "Field %s missing in right file %s"%(i, right_file)

    writer = csv.DictWriter(tf.io.gfile.GFile(out_file+'.tmp', 'w'),
                            fieldnames=left_fields + right_fields)
    writer.writeheader()

    for lline, rline in itertools.zip_longest(left_reader, right_reader):
        assert lline is not None, \
            "left file %s is shorter than right file %s"%(
                left_file, right_file)
        assert rline is not None, \
            "right file %s is shorter than left file %s"%(
                right_file, left_file)
        output = {i: lline[i] for i in left_fields}
        output.update({i: rline[i] for i in right_fields})
        writer.writerow(output)

    logging.info("Renaming %s.tmp to %s", out_file, out_file)
    tf.io.gfile.rename(out_file+'.tmp', out_file, overwrite=True)


def run(args):
    logging.basicConfig(level=logging.INFO)

    left_loader = DataBlockLoader(
        'local', None, args.left_data_path, args.left_file_ext,
        worker_rank=args.worker_rank, num_workers=args.num_workers,
        output_path=args.output_path)
    right_loader = DataBlockLoader(
        'local', None, args.right_data_path, args.right_file_ext,
        worker_rank=args.worker_rank, num_workers=args.num_workers,
        output_path=args.output_path)

    tf.io.gfile.makedirs(args.output_path)

    while True:
        left_block = left_loader.get_next_block()
        right_block = right_loader.get_next_block()
        if left_block is None:
            assert right_block is None
            break
        assert left_block.block_id == right_block.block_id, \
            "Block id does not match: %s vs %s"%(
                left_block.block_id, right_block.block_id)
        output_file = os.path.join(
            args.output_path, left_block.block_id + '.output')
        merge(args, left_block.data_path, right_block.data_path, output_file)

if __name__ == '__main__':
    run(create_argument_parser().parse_args())
