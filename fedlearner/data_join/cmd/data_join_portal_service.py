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
from fedlearner.data_join import DataJoinPortalService

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')
    parser = argparse.ArgumentParser(description='DataJointPortal cmd.')
    parser.add_argument('data_join_portal_name', type=str,
                        help='the name of data join portal')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:2379', help='the addrs of etcd')
    parser.add_argument('--etcd_base_dir', type=str,
                        default='fedlearner_protal_test',
                        help='the namespace of etcd key for data join portal')
    parser.add_argument('--raw_data_publish_dir', type=str, required=True,
                        help='the etcd base dir to publish new raw data')
    parser.add_argument('--use_mock_etcd', action='store_true',
                        help='use to mock etcd for test')
    parser.add_argument('--input_data_file_iter', type=str, default='TF_RECORD',
                        help='the type for iter of input data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type of input data file')
    parser.add_argument('--portal_reducer_buffer_size', type=int,
                        default=4096, help='the buffer size of portal reducer')
    parser.add_argument('--example_validator', type=str,
                        default='EXAMPLE_VALIDATOR',
                        help='the name of example validator')
    parser.add_argument('--validate_event_time', action='store_true',
                        help='validate the example has event time')
    args = parser.parse_args()
    options = dj_pb.DataJoinPotralOptions(
            example_validator=dj_pb.ExampleValidatorOptions(
                example_validator=args.example_validator,
                validate_event_time=args.validate_event_time
            ),
            reducer_buffer_size=args.portal_reducer_buffer_size,
            raw_data_options=dj_pb.RawDataOptions(
                raw_data_iter=args.input_data_file_iter,
                compressed_type=args.compressed_type
            ),
            raw_data_publish_dir=args.raw_data_publish_dir,
            use_mock_etcd=args.use_mock_etcd
        )
    portal_srv = DataJoinPortalService(
            args.listen_port, args.data_join_portal_name,
            args.etcd_name, args.etcd_addrs,
            args.etcd_base_dir, options,
        )
    portal_srv.run()
