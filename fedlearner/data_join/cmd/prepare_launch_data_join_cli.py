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

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common.db_client import DBClient
from fedlearner.common.common import set_logger
from fedlearner.data_join import common

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DataJoinMaster cmd.')
    parser.add_argument('--data_source_name', type=str, required=True,
                         help='the data source name')
    parser.add_argument('--partition_num', type=int, required=True,
                         help='the partition num for data source')
    parser.add_argument('--start_time', type=int, required=True,
                         help='the start time of data source')
    parser.add_argument('--end_time', type=int, required=True,
                         help='the end time of data source')
    parser.add_argument('--negative_sampling_rate', type=float, required=True,
                         help='the negative sampling rate for data source')
    parser.add_argument('--role', type=str, required=True,
                        help='the role of data join')
    parser.add_argument('--output_base_dir', type=str, required=True,
                        help='the directory of for output data for data join')
    parser.add_argument('--kvstore_type', type=str, default='etcd',
                        help='the type of kvstore')
    parser.add_argument('--raw_data_sub_dir', type=str, required=True,
                        help='the mysql base dir to subscribe new raw data')
    args = parser.parse_args()
    set_logger()
    data_source = common_pb.DataSource()
    data_source.data_source_meta.name = args.data_source_name
    data_source.data_source_meta.partition_num = args.partition_num
    data_source.data_source_meta.start_time = args.start_time
    data_source.data_source_meta.end_time = args.end_time
    data_source.data_source_meta.negative_sampling_rate = \
            args.negative_sampling_rate
    if args.role.upper() == 'LEADER':
        data_source.role = common_pb.FLRole.Leader
    else:
        assert args.role.upper() == 'FOLLOWER'
        data_source.role = common_pb.FLRole.Follower
    data_source.output_base_dir = args.output_base_dir
    data_source.raw_data_sub_dir = args.raw_data_sub_dir
    data_source.state = common_pb.DataSourceState.Init
    kvstore = DBClient(args.kvstore_type)
    master_kvstore_key = common.data_source_kvstore_base_dir(
            data_source.data_source_meta.name
        )
    raw_data = kvstore.get_data(master_kvstore_key)
    if raw_data is None:
        logging.info("data source %s is not existed", args.data_source_name)
        common.commit_data_source(kvstore, data_source)
        logging.info("apply new data source %s", args.data_source_name)
    else:
        logging.info("data source %s has been existed", args.data_source_name)
