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

import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.common.common import set_logger
from fedlearner.data_join.private_set_union.transmit import PSUTransmitterMaster
from fedlearner.data_join.private_set_union import parquet_utils as pqu
from fedlearner.data_join.private_set_union.utils import Paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PSUMasterService cmd.')
    parser.add_argument('--remote_address', '-r', type=str,
                        help='Address of remote master.')
    parser.add_argument('--remote_listen_port', '-rp', type=int, default=50051,
                        help='Listen port of remote connections.')
    parser.add_argument('--local_listen_port', '-lp', type=int, default=4032,
                        help='Listen port of inner connections.')
    parser.add_argument('--key_type', '-k', type=str, default='ECC',
                        help='Type of encryption keys.')
    parser.add_argument('--worker_num', '-w', type=int,
                        help='Num of transmit workers.')
    parser.add_argument('--role', type=str,
                        choices=['left', 'follower', 'right', 'leader'],
                        help='PSU role. Left/Follower will calculate union.')
    args = parser.parse_args()
    set_logger()

    key_type = getattr(psu_pb, args.key_type, None)
    if not key_type:
        raise ValueError(f'Key type {args.key_type} not registered!')

    # TODO(zhangzihui): file_paths
    # ======== Encrypt Phase ========
    file_paths = []
    master = PSUTransmitterMaster(remote_listen_port=args.remote_listen_port,
                                  remote_address=args.remote_address,
                                  local_listen_port=args.local_listen_port,
                                  phase=psu_pb.PSU_Encrypt,
                                  key_type=key_type,
                                  file_paths=file_paths,
                                  worker_num=args.worker_num)
    master.run()
    master.wait_for_finish()
    # ======== Sync Phase ========
    e2_files = pqu.list_parquet_files(Paths.encode_e2_dir())
    master.wait_to_enter_next_phase(e2_files)
    master.wait_for_finish()
    # ======== Union Phase ========
    if args.role == 'left' or args.role == 'follower':
        # TODO(zhangzihui): spark job for union
        pass
    # ======== L_Diff & R_Diff Phase ========
        l_diff, r_diff = Paths.encode_diff_output_paths()
        l_diff_files = pqu.list_parquet_files(l_diff)
        r_diff_files = pqu.list_parquet_files(r_diff)
    else:
        l_diff_files = []
        r_diff_files = []
    master.wait_to_enter_next_phase(l_diff_files)
    master.wait_to_enter_next_phase(r_diff_files)
    # ======== Reload Phase ========
    # TODO(zhangzihui): spark job for reload
