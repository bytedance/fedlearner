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

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common.common import set_logger
from fedlearner.data_join.data_join_master import DataJoinMasterService
from fedlearner.data_join.psi_rsa import rsa_psi_helper

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DataJointMasterService cmd.')
    parser.add_argument('peer_addr', type=str,
                        help='the addr(uuid) of peer data join master')
    parser.add_argument('--kvstore_type', type=str,
                        default='etcd', help='the name of mysql')
    parser.add_argument('--listen_port', '-p', type=int, default=4032,
                        help='Listen port of data join master')
    parser.add_argument('--data_source_name', type=str,
                        default='test_data_source',
                        help='the name of data source')
    parser.add_argument('--batch_mode', action='store_true',
                        help='make the data join run in batch mode')
    parser.add_argument('--rsa_length', type=int, required=False, default=2048,
                        help='RSA security length')
    parser.add_argument('--job_type', type=int, required=False, default=1,
                        help='data join task type, 0: PSI, 1: Streaming')
    parser.add_argument('--output_base_dir', type=str, required=True,
                        help='the directory of for output data for data join')
    parser.add_argument('--role', type=str, required=True,
                        help='the role of data join')
    args = parser.parse_args()
    set_logger()
    master_options = dj_pb.DataJoinMasterOptions(
            use_mock_etcd=(args.kvstore_type == 'mock'),
            batch_mode=args.batch_mode
        )
    master_srv = DataJoinMasterService(
            args.listen_port, args.peer_addr,
            args.data_source_name, args.kvstore_type,
            master_options
        )
    if args.job_type == common_pb.DataSourceType.PSI:
        if args.role == common_pb.FLRole.Leader:
            assert args.rsa_length >= 1024, "Invalid rsa_length for PSI"
            rsa_psi_helper.make_or_load_rsa_keypair_as_pem(
                args.rsa_length, args.output_base_dir)
        else:
            result = rsa_psi_helper.load_rsa_key_from_remote(
                args.peer_addr, args.output_base_dir)
            assert result, "Can't load rsa key from peer!"

    master_srv.run()
