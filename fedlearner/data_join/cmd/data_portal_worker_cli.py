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

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.data_join.data_portal_worker import DataPortalWorker
from fedlearner.data_join.common import get_kvstore_config

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format="%(asctime)s %(filename)s "\
                               "%(lineno)s %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description='DataJointPortal cmd.')
    parser.add_argument("--rank_id", type=int,
                        help="the rank id of this worker")
    parser.add_argument("--master_addr", type=str,
                        help="the addr of data portal master")
    parser.add_argument("--kvstore_type", type=str,
                        default='etcd', help='the type of kvstore')
    parser.add_argument("--use_mock_etcd", action="store_true",
                        help='use to mock mysql for test')
    parser.add_argument("--merger_read_ahead_size", type=int, default=128<<10,
                        help="the read ahead size for merger")
    parser.add_argument("--merger_read_batch_size", type=int, default=32,
                        help="the read batch size for merger")
    parser.add_argument("--input_data_file_iter", type=str, default="TF_RECORD",
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help="the type for input data iterator")
    parser.add_argument("--compressed_type", type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type of input data file')
    parser.add_argument('--read_ahead_size', type=int, default=1<<20,
                        help='the read ahead size for raw data')
    parser.add_argument('--read_batch_size', type=int, default=128,
                        help='the read batch size for tf record iter')
    parser.add_argument('--output_builder', type=str, default='TF_RECORD',
                        choices=['TF_RECORD', 'CSV_DICT'],
                        help='the builder for ouput file')
    parser.add_argument('--builder_compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the builder for ouput file')
    parser.add_argument("--batch_size", type=int, default=1024,
                        help="the batch size for raw data reader")
    parser.add_argument('--memory_limit_ratio', type=int, default=70,
                        choices=range(40, 80),
                        help='the ratio(*100) of memory used for map&reduce')

    args = parser.parse_args()
    if args.input_data_file_iter == 'TF_RECORD' or \
            args.output_builder == 'TF_RECORD':
        import tensorflow
        tensorflow.compat.v1.enable_eager_execution()

    portal_worker_options = dp_pb.DataPortalWorkerOptions(
        raw_data_options=dj_pb.RawDataOptions(
            raw_data_iter=args.input_data_file_iter,
            compressed_type=args.compressed_type,
            read_ahead_size=args.read_ahead_size,
            read_batch_size=args.read_batch_size
        ),
        writer_options=dj_pb.WriterOptions(
            output_writer=args.output_builder,
            compressed_type=args.builder_compressed_type
        ),
        batch_processor_options=dj_pb.BatchProcessorOptions(
            batch_size=args.batch_size,
            max_flying_item=-1
        ),
        merger_read_ahead_size=args.merger_read_ahead_size,
        merger_read_batch_size=args.merger_read_batch_size,
        memory_limit_ratio=args.memory_limit_ratio/100
    )
    db_database, db_addr, db_username, db_password, db_base_dir = \
        get_kvstore_config(args.kvstore_type)
    data_portal_worker = DataPortalWorker(
            portal_worker_options, args.master_addr,
            args.rank_id, db_database, db_base_dir,
            db_addr, db_username, db_password,
            (args.kvstore_type == 'mock')
        )
    data_portal_worker.start()
