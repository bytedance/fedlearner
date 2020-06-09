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
import os

from tensorflow.compat.v1 import gfile

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join.rsa_psi.rsa_psi_preprocessor import RsaPsiPreProcessor

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='Rsa Psi Preprocessor!')
    parser.add_argument('--preprocessor_name', type=str, default='test',
                        help='the name of rsa psi preprocessor')
    parser.add_argument('-r', '--psi_role', type=str, required=True,
                        choices=['leader', 'follower'],
                        help='the role of rsa psi(leader/follower)')
    parser.add_argument('--rsa_key_path', type=str,
                        help='the file path for the rsa key')
    parser.add_argument('--rsa_key_pem', type=str,
                        help='the rsa key stroe by pem format')
    parser.add_argument('--input_file_paths', type=str, nargs='+',
                        help='the file path input rsa psi preprocessor')
    parser.add_argument('--input_dir', type=str,
                        help='the raw data file appointed by dir')
    parser.add_argument('--output_file_dir', type=str, required=True,
                        help='the directory to store the result of processor')
    parser.add_argument('--raw_data_publish_dir', type=str, required=True,
                        help='the etcd base dir to publish new raw data')
    parser.add_argument('--leader_rsa_psi_signer_addr', type=str,
                        help='the ras psi follower should set give '\
                             'the addr of rsa psi signer of leader')
    parser.add_argument('--process_batch_size', type=int, default=1024,
                        help='the batch size for preprocessor')
    parser.add_argument('--max_flying_item', type=int, default=1<<20,
                        help='the process buffer size')
    parser.add_argument('--offload_processor_number', type=int, default=1,
                        help='the number of processor to offload rsa compute')
    parser.add_argument('--max_flying_sign_batch', type=int, default=32,
                        help='the max flying sign batch')
    parser.add_argument('--max_flying_sign_rpc', type=int, default=16,
                        help='the max flying sign rpc request')
    parser.add_argument('--sign_rpc_timeout_ms', type=int, default=0,
                        help='the rpc time ms for rpc sign')
    parser.add_argument('--stub_fanout', type=int, default=2,
                        help='the max stub for follower of rpc of processor')
    parser.add_argument('--slow_sign_threshold', type=int, default=10,
                        help='the threshold to record as slow sign')
    parser.add_argument('--sort_run_merger_read_ahead_buffer', type=int,
                        default=1<<20, help='the read ahead buffer for the '\
                                            'reader of sort run reader')
    parser.add_argument('--rpc_sync_mode', action='store_true',
                        help='use the sync mode for rpc sign')
    parser.add_argument('--rpc_thread_pool_size', type=int, default=16,
                        help='the thread pool size for sync rpc sign')
    parser.add_argument('--partition_id', type=int, required=True,
                        help='the partition id will be processed')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:2379', help='the addrs of etcd')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')

    args = parser.parse_args()
    all_fpaths = []
    if args.input_file_paths is not None:
        for fp in args.input_file_paths:
            all_fpaths.append(fp)
    if args.input_dir is not None:
        all_fpaths += [os.path.join(args.input_dir, f)
                       for f in gfile.ListDirectory(args.input_dir)]
    if len(all_fpaths) == 0:
        raise RuntimeError("no input files for preprocessor")
    rsa_key_pem = args.rsa_key_pem
    if rsa_key_pem is None or len(rsa_key_pem) == 0:
        assert args.rsa_key_path is not None
        with gfile.GFile(args.rsa_key_path, 'rb') as f:
            rsa_key_pem = f.read()
    preprocessor_options = dj_pb.RsaPsiPreProcessorOptions(
            preprocessor_name=args.preprocessor_name,
            role=common_pb.FLRole.Leader if args.psi_role == 'leader' \
                                         else common_pb.FLRole.Follower,
            rsa_key_pem=rsa_key_pem,
            input_file_paths=list(set(all_fpaths)),
            output_file_dir=args.output_file_dir,
            raw_data_publish_dir=args.raw_data_publish_dir,
            partition_id=args.partition_id,
            leader_rsa_psi_signer_addr=args.leader_rsa_psi_signer_addr,
            offload_processor_number=args.offload_processor_number,
            max_flying_sign_batch=args.max_flying_sign_batch,
            max_flying_sign_rpc=args.max_flying_sign_rpc,
            sign_rpc_timeout_ms=args.sign_rpc_timeout_ms,
            stub_fanout=args.stub_fanout,
            slow_sign_threshold=args.slow_sign_threshold,
            rpc_sync_mode=args.rpc_sync_mode,
            rpc_thread_pool_size=args.rpc_thread_pool_size,
            sort_run_merger_read_ahead_buffer=\
                args.sort_run_merger_read_ahead_buffer,
            batch_processor_options=dj_pb.BatchProcessorOptions(
                batch_size=args.process_batch_size,
                max_flying_item=args.max_flying_item
            )
        )
    preprocessor = RsaPsiPreProcessor(preprocessor_options, args.etcd_name,
                                      args.etcd_addrs, args.etcd_base_dir)
    preprocessor.start_process()
    logging.info("PreProcessor launched for %s of RSA PSI", args.psi_role)
    preprocessor.wait_for_finished()
    logging.info("PreProcessor finished for %s of RSA PSI", args.psi_role)
