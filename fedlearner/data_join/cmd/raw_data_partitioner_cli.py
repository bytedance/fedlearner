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

import logging
import argparse
from fnmatch import fnmatch
import os

from cityhash import CityHash32 # pylint: disable=no-name-in-module
import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.raw_data_partitioner import RawDataPartitioner

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='Raw Data Partitioner')
    parser.add_argument('--partitioner_name', type=str, default='test',
                        help='the name of raw data partitioner')
    parser.add_argument('--file_paths', type=str, nargs='+',
                        help='the raw data file appointed by file path')
    parser.add_argument('--input_dir', type=str, required=True,
                        help='the raw data file appointed by dir')
    parser.add_argument('--input_file_wildcard', type=str,
                        help='the wildcard filter for input file')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='the directory to store the result of processor')
    parser.add_argument('--output_partition_num', type=int, required=True,
                        help='the output partition number')
    parser.add_argument('--raw_data_iter', type=str, default='CSV_DICT',
                        choices=['TF_RECORD', 'CSV_DICT', 'TF_DATASET'],
                        help='the type for raw data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for raw data')
    parser.add_argument('--read_ahead_size', type=int, default=64<<20,
                        help='the read ahead size for raw data,'
                             'only support CSV DICT')
    parser.add_argument('--tf_eager_mode', action='store_true',
                        help='use the eager_mode for tf')
    parser.add_argument('--output_builder', type=str, default='TF_RECORD',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the builder for ouput file')
    parser.add_argument('--builder_compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for TF_RECORD builder')
    parser.add_argument('--raw_data_batch_size', type=int, default=2048,
                        help='the batch size to load raw data')
    parser.add_argument('--max_flying_raw_data', type=int, default=2<<20,
                        help='max flying raw data cached output')
    parser.add_argument('--total_partitioner_num', type=int, required=True,
                        help='the number of partitioner worker for input data')
    parser.add_argument('--partitioner_rank_id', type=int, required=True,
                        help='the rank id of partitioner')
    parser.add_argument('--etcd_name', type=str, default='test_etcd',
                        help='the name of etcd cluster')
    parser.add_argument('--etcd_addrs', type=str, default='localhost:2379',
                        help='the addrs of etcd server')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')
    parser.add_argument('--part_field', type=str, default='raw_id',
                        help='the field for raw data partition')

    args = parser.parse_args()
    if args.tf_eager_mode:
        tf.enable_eager_execution()
    assert 0 <= args.partitioner_rank_id < args.total_partitioner_num
    all_fpaths = []
    if args.file_paths is not None:
        for fp in args.file_paths:
            all_fpaths.append(fp)
    if args.input_dir is not None:
        all_fpaths += [os.path.join(args.input_dir, f)
                       for f in gfile.ListDirectory(args.input_dir)]
    if args.input_file_wildcard is not None and \
            len(args.input_file_wildcard) > 0:
        all_fpaths = [fpath for fpath in all_fpaths
                      if fnmatch(fpath, args.input_file_wildcard)]
    if len(all_fpaths) == 0:
        raise RuntimeError("no input files for partitioner")
    all_fpaths = list(set(all_fpaths))
    all_fpaths.sort()
    partitioner_num = args.total_partitioner_num
    if partitioner_num > 1:
        origin_file_num = len(all_fpaths)
        all_fpaths = \
            [fpath for fpath in all_fpaths
             if CityHash32(os.path.basename(fpath)) %  partitioner_num == \
                     args.partitioner_rank_id]
        logging.info("Partitioner of rank id %d will process %d/%d "\
                     "input files", args.partitioner_rank_id,
                     len(all_fpaths), origin_file_num)
    partitioner_options = dj_pb.RawDataPartitionerOptions(
            partitioner_name=args.partitioner_name,
            input_file_paths=all_fpaths,
            output_dir=args.output_dir,
            output_partition_num=args.output_partition_num,
            raw_data_options=dj_pb.RawDataOptions(
                raw_data_iter=args.raw_data_iter,
                compressed_type=args.compressed_type,
                read_ahead_size=args.read_ahead_size
            ),
            writer_options=dj_pb.WriterOptions(
                output_writer=args.output_builder,
                compressed_type=args.builder_compressed_type,
            ),
            partitioner_rank_id=args.partitioner_rank_id,
            batch_processor_options=dj_pb.BatchProcessorOptions(
                batch_size=args.raw_data_batch_size,
                max_flying_item=args.max_flying_raw_data
            )
        )
    partitioner = RawDataPartitioner(partitioner_options, args.part_field,
                                     args.etcd_name, args.etcd_addrs,
                                     args.etcd_base_dir)
    logging.info("RawDataPartitioner %s of rank %d launched",
                 partitioner_options.partitioner_name,
                 partitioner_options.partitioner_rank_id)
    partitioner.start_process()
    partitioner.wait_for_finished()
    logging.info("RawDataPartitioner %s of rank %d finished",
                 partitioner_options.partitioner_name,
                 partitioner_options.partitioner_rank_id)
