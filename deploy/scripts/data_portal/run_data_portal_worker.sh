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
source /app/deploy/scripts/pre_start_hook.sh || true
source /app/deploy/scripts/env_to_args.sh 

MASTER_POD_NAMES=`python -c 'import json, os; print(json.loads(os.environ["CLUSTER_SPEC"])["clusterSpec"]["Master"][0])'`

merger_read_ahead_size=$(normalize_env_to_args "--merger_read_ahead_size" $MERGE_READ_AHEAD_SIZE)
merger_read_batch_size=$(normalize_env_to_args "--merger_read_batch_size" $MERGE_READ_BATCH_SIZE)
input_data_file_iter=$(normalize_env_to_args "--input_data_file_iter" $INPUT_DATA_FORMAT)
compressed_type=$(normalize_env_to_args "--compressed_type" $COMPRESSED_TYPE)
read_ahead_size=$(normalize_env_to_args "--read_ahead_size" $READ_AHEAD_SIZE)
read_batch_size=$(normalize_env_to_args "--read_batch_size" $READ_BATCH_SIZE)
output_builder=$(normalize_env_to_args "--output_builder" $OUTPUT_DATA_FORMAT)
builder_compressed_type=$(normalize_env_to_args "--builder_compressed_type" $BUILDER_COMPRESSED_TYPE)
batch_size=$(normalize_env_to_args "--batch_size" $BATCH_SIZE)
kvstore_type=$(normalize_env_to_args '--kvstore_type' $KVSTORE_TYPE)
memory_limit_ratio=$(normalize_env_to_args '--memory_limit_ratio' $MEMORY_LIMIT_RATIO)
optional_fields=$(normalize_env_to_args '--optional_fields' $OPTIONAL_FIELDS)
input_data_validation_ratio=$(normalize_env_to_args '--input_data_validation_ratio' $INPUT_DATA_VALIDATION_RATIO)


python -m fedlearner.data_join.cmd.data_portal_worker_cli \
  --rank_id=$INDEX \
  --master_addr=$MASTER_POD_NAMES \
  $input_data_file_iter $compressed_type $read_ahead_size $read_batch_size \
  $output_builder $builder_compressed_type \
  $batch_size $kvstore_type $memory_limit_ratio \
  $optional_fields $input_data_validation_ratio

