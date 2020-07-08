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
from fedlearner.data_join.data_portal_worker import DataPortalWorker

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='DataJointPortal cmd.')
    parser.add_argument("--rank_id", type=int,
                        help="the rank id of this worker")
    parser.add_argument("--master_addr", type=str,
                        help="the addr of data portal master")
    parser.add_argument("--etcd_name", type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument("--etcd_addrs", type=str,
                        default="localhost:2379", help="the addrs of etcd")
    parser.add_argument("--etcd_base_dir", type=str,
                        help="the namespace of etcd key for data portal worker")
    parser.add_argument("--use_mock_etcd", action="store_true",
                        help='use to mock etcd for test')
    parser.add_argument("--merge_buffer_size", type=int,
                        default=4096, help="the buffer size for merging")
    parser.add_argument("--write_buffer_size", type=int,
                        default=10485760,
                        help="the output buffer size (bytes) for partitioner")
    parser.add_argument("--input_data_file_iter", type=str, default="TF_RECORD",
                        help="the type for input data iterator")
    parser.add_argument("--compressed_type", type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type of input data file')
    parser.add_argument("--batch_size", type=int, default=1024,
                        help="the batch size for raw data reader")
    parser.add_argument("--max_flying_item", type=int, default=300000,
                        help='the maximum items processed at the same time')
    args = parser.parse_args()
    raw_data_options = dj_pb.RawDataOptions(
        raw_data_iter=args.input_data_file_iter,
        compressed_type=args.compressed_type)
    batch_processor_options = dj_pb.BatchProcessorOptions(
        batch_size=args.batch_size,
        max_flying_item=args.max_flying_item)
    partitioner_options = dj_pb.RawDataPartitionerOptions(
        partitioner_name="dp_worker_partitioner_{}".format(args.rank_id),
        raw_data_options=raw_data_options,
        batch_processor_options=batch_processor_options,
        output_item_threshold=args.write_buffer_size)
    merge_options = dj_pb.MergeOptions(
        merger_name="dp_worker_merger_{}".format(args.rank_id),
        raw_data_options=raw_data_options,
        batch_processor_options=batch_processor_options,
        merge_buffer_size=args.merge_buffer_size,
        output_item_threshold=args.write_buffer_size)

    portal_worker_options = dj_pb.DataPortalWorkerOptions(
        partitioner_options=partitioner_options,
        merge_options=merge_options)

    data_portal_worker = DataPortalWorker(portal_worker_options,
        args.master_addr, args.rank_id, args.etcd_name,
        args.etcd_base_dir, args.etcd_addrs, args.use_mock_etcd)

    data_portal_worker.start()
