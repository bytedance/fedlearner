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
from google.protobuf import text_format

from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.common.db_client import DBClient
from fedlearner.common.common import set_logger

from fedlearner.data_join import common
from fedlearner.data_join.data_portal_master import DataPortalMasterService

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DataPortalMasterService cmd.')
    parser.add_argument('--kvstore_type', type=str,
                        default='etcd', help='the type of kvstore')
    parser.add_argument('--listen_port', '-p', type=int, default=4032,
                        help='Listen port of data join master')
    parser.add_argument('--data_portal_name', type=str,
                        default='test_data_source',
                        help='the name of data source')
    parser.add_argument('--data_portal_type', type=str,
                        default='Streaming', choices=['PSI', 'Streaming'],
                        help='the type of data portal type')
    parser.add_argument('--output_partition_num', type=int, required=True,
                        help='the output partition number of data portal')
    parser.add_argument('--input_file_wildcard', type=str, default='',
                        help='the wildcard filter for input file')
    parser.add_argument('--input_base_dir', type=str, required=True,
                        help='the base dir of input directory')
    parser.add_argument('--output_base_dir', type=str, required=True,
                        help='the base dir of output directory')
    parser.add_argument('--raw_data_publish_dir', type=str, required=True,
                        help='the raw data publish dir in mysql')
    parser.add_argument('--long_running', action='store_true',
                        help='make the data portal long running')
    parser.add_argument('--check_success_tag', action='store_true',
                        help='Check that a _SUCCESS file exists before '
                             'processing files in a subfolder')
    parser.add_argument('--single_subfolder', action='store_true',
                        help='Only process one subfolder at a time')
    parser.add_argument('--files_per_job_limit', type=int, default=None,
                        help='Max number of files in a job')
    args = parser.parse_args()
    set_logger()

    use_mock_etcd = (args.kvstore_type == 'mock')
    kvstore = DBClient(args.kvstore_type, use_mock_etcd)
    kvstore_key = common.portal_kvstore_base_dir(args.data_portal_name)
    if kvstore.get_data(kvstore_key) is None:
        portal_manifest = dp_pb.DataPortalManifest(
                name=args.data_portal_name,
                data_portal_type=(dp_pb.DataPortalType.PSI if
                                  args.data_portal_type == 'PSI' else
                                  dp_pb.DataPortalType.Streaming),
                output_partition_num=args.output_partition_num,
                input_file_wildcard=args.input_file_wildcard,
                input_base_dir=args.input_base_dir,
                output_base_dir=args.output_base_dir,
                raw_data_publish_dir=args.raw_data_publish_dir,
                processing_job_id=-1
            )
        kvstore.set_data(kvstore_key, text_format.\
            MessageToString(portal_manifest))

    options = dp_pb.DataPotraMasterlOptions(
        use_mock_etcd=use_mock_etcd,
        long_running=args.long_running,
        check_success_tag=args.check_success_tag,
        single_subfolder=args.single_subfolder,
        files_per_job_limit=args.files_per_job_limit)

    portal_master_srv = DataPortalMasterService(args.listen_port,
                                                args.data_portal_name,
                                                args.kvstore_type,
                                                options)
    portal_master_srv.run()
