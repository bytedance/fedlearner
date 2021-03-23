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

import tensorflow

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common.argparse_util import str_as_bool
from fedlearner.common.common import set_logger
from fedlearner.data_join.data_join_worker import DataJoinWorkerService
from fedlearner.data_join.common import interval_to_timestamp
tensorflow.compat.v1.enable_eager_execution()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DataJoinWorkerService cmd.')
    parser.add_argument('peer_addr', type=str,
                        help='the addr(uuid) of peer data join worker')
    parser.add_argument('master_addr', type=str,
                        help='the addr(uuid) of local data join master')
    parser.add_argument('rank_id', type=int,
                        help='the rank id for this worker')
    parser.add_argument('--kvstore_type', type=str,
                        default='etcd', help='the type of kvstore')
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
    parser.add_argument('--data_block_builder', type=str, default='TF_RECORD',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the file type for data block')
    parser.add_argument('--data_block_compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type for data block')
    parser.add_argument('--max_conversion_delay', type=str, default="7D",
                        help='the max delay of an impression occurred '\
                        'before a conversion as an attribution pair, unit: '\
                        '{Y|M|D|H|N|S}, i.e. 1N20S equals 80 seconds')
    parser.add_argument('--enable_negative_example_generator', type=str_as_bool,
                        default=False, const=True, nargs='?',
                        help="enable the negative example auto-generator, "\
                        "filled with label: 0")
    parser.add_argument('--negative_sampling_rate', type=float, default=0.1,
                        help="the rate of sampling when auto-generating "\
                        "negative example, in [0.0, 1.0)")
    parser.add_argument('--join_expr', type=str, default="example_id",
                        help="join expression for universal joiner")
    parser.add_argument('--negative_sampling_filter_expr', type=str,
                        help="negative sample filter expression, only be "
                        " avaliable for follower")
    parser.add_argument('--join_key_mapper', type=str, default="DEFAULT",
                        help="key mapper name")
    parser.add_argument('--raw_data_cache_type', type=str, default="memory",
                        choices=["memory", "disk"],
                        help="the space to store the raw data")
    parser.add_argument('--optional_fields', type=str, default='',
                        help='optional stat fields used in joiner, separated '
                             'by comma between fields, e.g. "label,rit". '
                             'Each field will be stripped.')
    args = parser.parse_args()
    set_logger()
    optional_fields = list(
        field for field in map(str.strip, args.optional_fields.split(','))
        if field != ''
    )
    worker_options = dj_pb.DataJoinWorkerOptions(
            use_mock_etcd=(args.kvstore_type == 'mock'),
            raw_data_options=dj_pb.RawDataOptions(
                    raw_data_iter=args.raw_data_iter,
                    compressed_type=args.compressed_type,
                    read_ahead_size=args.read_ahead_size,
                    read_batch_size=args.read_batch_size,
                    optional_fields=optional_fields,
                    raw_data_cache_type=args.raw_data_cache_type
                ),
            example_joiner_options=dj_pb.ExampleJoinerOptions(
                    example_joiner=args.example_joiner,
                    min_matching_window=args.min_matching_window,
                    max_matching_window=args.max_matching_window,
                    data_block_dump_interval=args.data_block_dump_interval,
                    data_block_dump_threshold=args.data_block_dump_threshold,
                    max_conversion_delay=interval_to_timestamp(\
                                            args.max_conversion_delay),
                    enable_negative_example_generator=\
                        args.enable_negative_example_generator,
                    negative_sampling_rate=\
                        args.negative_sampling_rate,
                    join_expr=args.join_expr,
                    join_key_mapper=args.join_key_mapper,
                    negative_sampling_filter_expr=\
                        args.negative_sampling_filter_expr,
                ),
            example_id_dump_options=dj_pb.ExampleIdDumpOptions(
                    example_id_dump_interval=args.example_id_dump_interval,
                    example_id_dump_threshold=args.example_id_dump_threshold
                ),
            batch_processor_options=dj_pb.BatchProcessorOptions(
                    batch_size=4096,
                    max_flying_item=-1
                ),
            data_block_builder_options=dj_pb.WriterOptions(
                    output_writer=args.data_block_builder,
                    compressed_type=args.data_block_compressed_type
                )
        )
    worker_srv = DataJoinWorkerService(args.listen_port, args.peer_addr,
                                       args.master_addr, args.rank_id,
                                       args.kvstore_type, worker_options)
    worker_srv.run()
