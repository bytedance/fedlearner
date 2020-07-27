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
import logging

import tensorflow

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.data_join_worker import DataJoinWorkerService
tensorflow.compat.v1.enable_eager_execution()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='DataJoinWorkerService cmd.')
    parser.add_argument('peer_addr', type=str,
                        help='the addr(uuid) of peer data join worker')
    parser.add_argument('master_addr', type=str,
                        help='the addr(uuid) of local data join master')
    parser.add_argument('rank_id', type=int,
                        help='the rank id for this worker')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:4578', help='the addrs of etcd')
    parser.add_argument('--use_mock_etcd', action='store_true',
                        help='use to mock etcd for test')
    parser.add_argument('--listen_port', '-p', type=int, default=4132,
                        help='Listen port of data join master')
    parser.add_argument('--raw_data_iter', type=str, default='TF_RECORD',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the type for raw data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for raw data')
    parser.add_argument('--read_ahead_size', type=int, default=32<<20,
                        help='the read ahead size for raw data')
    parser.add_argument('--read_batch_size', type=int, default=128,
                        help='the read batch size for tf record iter')
    parser.add_argument('--example_joiner', type=str,
                        default='STREAM_JOINER',
                        help='the method for example joiner')
    parser.add_argument('--min_matching_window', type=int, default=1024,
                        help='the min matching window for example join. '\
                             '<=0 means window size is infinite')
    parser.add_argument('--max_matching_window', type=int, default=4096,
                        help='the max matching window for example join. '\
                             '<=0 means window size is infinite')
    parser.add_argument('--data_block_dump_interval', type=int, default=-1,
                        help='dump a data block every interval, <=0'\
                             'means no time limit for dumping data block')
    parser.add_argument('--data_block_dump_threshold', type=int, default=4096,
                        help='dump a data block if join N example, <=0'\
                             'means no size limit for dumping data block')
    parser.add_argument('--example_id_dump_interval', type=int, default=-1,
                        help='dump leader example id interval, <=0'\
                             'means no time limit for dumping example id')
    parser.add_argument('--example_id_dump_threshold', type=int, default=4096,
                        help='dump a data block if N example id, <=0'\
                             'means no size limit for dumping example id')
    parser.add_argument('--example_id_batch_size', type=int, default=4096,
                        help='size of example id batch combined for '\
                             'example id sync leader')
    parser.add_argument('--max_flying_example_id', type=int, default=268435456,
                        help='max flying example id cached for '\
                             'example id sync leader')
    parser.add_argument('--data_block_builder', type=str, default='TF_RECORD',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the file type for data block')
    parser.add_argument('--data_block_compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for data block')
    args = parser.parse_args()
    worker_options = dj_pb.DataJoinWorkerOptions(
            use_mock_etcd=args.use_mock_etcd,
            raw_data_options=dj_pb.RawDataOptions(
                    raw_data_iter=args.raw_data_iter,
                    compressed_type=args.compressed_type,
                    read_ahead_size=args.read_ahead_size,
                    read_batch_size=args.read_batch_size
                ),
            example_joiner_options=dj_pb.ExampleJoinerOptions(
                    example_joiner=args.example_joiner,
                    min_matching_window=args.min_matching_window,
                    max_matching_window=args.max_matching_window,
                    data_block_dump_interval=args.data_block_dump_interval,
                    data_block_dump_threshold=args.data_block_dump_threshold,
                ),
            example_id_dump_options=dj_pb.ExampleIdDumpOptions(
                    example_id_dump_interval=args.example_id_dump_interval,
                    example_id_dump_threshold=args.example_id_dump_threshold
                ),
            batch_processor_options=dj_pb.BatchProcessorOptions(
                    batch_size=args.example_id_batch_size,
                    max_flying_item=args.max_flying_example_id
                ),
            data_block_builder_options=dj_pb.WriterOptions(
                    output_writer=args.data_block_builder,
                    compressed_type=args.data_block_compressed_type
                )
        )
    worker_srv = DataJoinWorkerService(args.listen_port, args.peer_addr,
                                       args.master_addr, args.rank_id,
                                       args.etcd_name, args.etcd_base_dir,
                                       args.etcd_addrs, worker_options)
    worker_srv.run()
