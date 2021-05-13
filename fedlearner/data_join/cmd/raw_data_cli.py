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

from fedlearner.common.common import set_logger
from fedlearner.data_join.raw_data.raw_data_job import RawDataJob
from fedlearner.data_join.raw_data.raw_data_config import SparkDriverConfig, \
    SparkExecutorConfig


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_portal_name', type=str, required=True,
                        help="job name")
    parser.add_argument('--data_portal_type', type=str,
                        default='Streaming', choices=['PSI', 'Streaming'],
                        help='the type of data portal type')
    parser.add_argument('--input_base_dir', type=str, required=True,
                        help='the base dir of input directory')
    parser.add_argument('--output_base_dir', type=str, required=True,
                        help='the base dir of output directory')
    parser.add_argument('--output_partition_num', type=int, required=True,
                        help='the output partition number of data portal')
    parser.add_argument('--raw_data_publish_dir', type=str, required=True,
                        help='the raw data publish dir in mysql')
    parser.add_argument('--upload_dir', type=str, required=True,
                        help='Upload directory for spark scripts')
    parser.add_argument('--check_success_tag', action='store_true',
                        help='Check that a _SUCCESS file exists before '
                             'processing files in a subfolder')
    parser.add_argument('--input_file_wildcard', type=str, default='',
                        help='the wildcard filter for input file')
    parser.add_argument('--single_subfolder', action="store_true",
                        help="run single subfolder per round")
    parser.add_argument('--files_per_job_limit', type=int, default=0,
                        help="Number of files per job")
    parser.add_argument("--output_type", type=str, default='raw_data',
                        choices=['raw_data', 'data_block'],
                        help='output type of data')
    parser.add_argument("--data_source_name", type=str, default="",
                        help='data source name to output')
    parser.add_argument("--data_block_dump_threshold", type=int, default=0,
                        help='Dumped threshold for data block')
    parser.add_argument('--long_running', action='store_true',
                        help='make the data portal long running')
    parser.add_argument("--spark_master_cores", type=int, default=0,
                        help='Number of cores of spark master')
    parser.add_argument("--spark_master_memory", type=str, default='',
                        help='Number of memory of spark master(same format '
                             'with spark config, e.g. 5g)')
    parser.add_argument("--spark_worker_cores", type=int, default=0,
                        help='Number of cores of spark worker')
    parser.add_argument("--spark_worker_memory", type=str, default='',
                        help='Number of memory of spark worker(same format '
                             'with spark config, e.g. 5g)')
    parser.add_argument("--spark_worker_instances", type=int, default=0,
                        help='Number of instances of spark worker')
    args = parser.parse_args()
    set_logger()
    spark_driver_config = SparkDriverConfig(args.spark_master_cores,
                                            args.spark_master_memory)
    spark_executor_config = SparkExecutorConfig(args.spark_worker_cores,
                                                args.spark_worker_memory,
                                                args.spark_worker_instances)

    job = RawDataJob(args.data_portal_name,
                     args.output_base_dir,
                     job_type=args.data_portal_type,
                     wildcard=args.input_file_wildcard,
                     output_type=args.output_type,
                     output_partition_num=args.output_partition_num,
                     data_source_name=args.data_source_name,
                     data_block_threshold=args.data_block_dump_threshold,
                     check_success_tag=args.check_success_tag,
                     single_subfolder=args.single_subfolder,
                     files_per_job_limit=args.files_per_job_limit,
                     raw_data_publish_dir=args.raw_data_publish_dir,
                     upload_dir=args.upload_dir,
                     spark_driver_config=spark_driver_config,
                     spark_executor_config=spark_executor_config)
    job.run(args.input_base_dir)
