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
input_file_wildcard=$(normalize_env_to_args "--input_file_wildcard" "$FILE_WILDCARD")
raw_data_iter=$(normalize_env_to_args "--raw_data_iter" $FILE_FORMAT)
compressed_type=$(normalize_env_to_args "--compressed_type" $COMPRESSED_TYPE)
read_ahead_size=$(normalize_env_to_args "--read_ahead_size" $READ_AHEAD_SIZE)
read_batch_size=$(normalize_env_to_args "--read_batch_size" $READ_BATCH_SIZE)
output_builder=$(normalize_env_to_args "--output_builder" $FILE_FORMAT)
builder_compressed_type=$(normalize_env_to_args "--builder_compressed_type" $BUILDER_COMPRESSED_TYPE)

file_paths=$(normalize_env_to_args "--file_paths" $INPUT_FILE_PATHS)
kvstore_type=$(normalize_env_to_args "--kvstore_type" $KVSTORE_TYPE) 
memory_limit_ratio=$(normalize_env_to_args '--memory_limit_ratio' $MEMORY_LIMIT_RATIO)

python -m fedlearner.data_join.cmd.raw_data_partitioner_cli \
    --input_dir=$INPUT_DIR \
    --output_dir=$OUTPUT_DIR \
    --output_partition_num=$OUTPUT_PARTITION_NUM \
    --total_partitioner_num=$TOTAL_PARTITIONER_NUM \
    --partitioner_rank_id=$INDEX \
    $partitioner_name $kvstore_type\
    $raw_data_iter $compressed_type $read_ahead_size $read_batch_size \
    $output_builder $builder_compressed_type \
    $file_paths $input_file_wildcard $memory_limit_ratio
