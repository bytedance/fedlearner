#!/bin/bash

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

set -ex

export CUDA_VISIBLE_DEVICES=
source /app/deploy/scripts/hdfs_common.sh || true
source /app/deploy/scripts/env_to_args.sh

partitioner_name=$(normalize_env_to_args "--partitioner_name" $NAME)
raw_data_batch_size=$(normalize_env_to_args "--raw_data_batch_size" $RAW_DATA_BATCH_SIZE)
max_flying_raw_data=$(normalize_env_to_args "--max_flying_raw_data" $MAX_FLYING_RAW_DATA)
input_file_wildcard=$(normalize_env_to_args "--input_file_wildcard" $FILE_WILDCARD)
raw_data_iter=$(normalize_env_to_args "--raw_data_iter" $FILE_FORMAT)
output_builder=$(normalize_env_to_args "--output_builder" $FILE_FORMAT)
compressed_type=$(normalize_env_to_args "--compressed_type" $COMPRESSED_TYPE)
read_ahead_size=$(normalize_env_to_args "--read_ahead_size" $READ_AHEAD_SIZE)
output_item_threshold=$(normalize_env_to_args "--output_item_threshold" $OUTPUT_ITEM_THRESHOLD)
file_paths=$(normalize_env_to_args "--file_paths" $INPUT_FILE_PATHS)

python -m fedlearner.data_join.cmd.raw_data_partitioner_cli \
    --input_dir=$INPUT_DIR \
    --output_dir=$OUTPUT_DIR \
    --output_partition_num=$OUTPUT_PARTITION_NUM \
    --total_partitioner_num=$TOTAL_PARTITIONER_NUM \
    --partitioner_rank_id=$INDEX \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    $partitioner_name $raw_data_batch_size $max_flying_raw_data \
    $input_file_wildcard $raw_data_iter $output_builder $compressed_type \
    $read_ahead_size $file_paths $TF_EAGER_MODE
