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
from fedlearner.common.common import set_logger
from fedlearner.data_join.data_join_master import DataJoinMasterService

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
    master_srv.run()
