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

MASTER_POD_NAMES=`python -c 'import json, os; print(json.loads(os.environ["CLUSTER_SPEC"])["clusterSpec"]["Master"][0])'`

raw_data_iter=$(normalize_env_to_args "--raw_data_iter" $RAW_DATA_ITER)
compressed_type=$(normalize_env_to_args "--compressed_type" $COMPRESSED_TYPE)
read_ahead_size=$(normalize_env_to_args "--read_ahead_size" $READ_AHEAD_SIZE)
example_joiner=$(normalize_env_to_args "--example_joiner" $EXAMPLE_JOINER)
min_matching_window=$(normalize_env_to_args "--min_matching_window" $MIN_MATCHING_WINDOW)
max_matching_window=$(normalize_env_to_args "--max_matching_window" $MAX_MATCHING_WINDOW)
data_block_dump_interval=$(normalize_env_to_args "--data_block_dump_interval" $DATA_BLOCK_DUMP_THRESHOLD)
data_block_dump_threshold=$(normalize_env_to_args "--data_block_dump_threshold" $DATA_BLOCK_DUMP_THRESHOLD)
example_id_dump_interval=$(normalize_env_to_args "--example_id_dump_interval" $EXAMPLE_ID_DUMP_INTERVAL)
example_id_dump_threshold=$(normalize_env_to_args "--example_id_dump_threshold" $EXAMPLE_ID_DUMP_THRESHOLD)
example_id_batch_size=$(normalize_env_to_args "--example_id_batch_size" $EXAMPLE_ID_BATCH_SIZE)
max_flying_example_id=$(normalize_env_to_args "--max_flying_example_id" $MAX_FLYING_EXAMPLE_ID)
data_block_builder=$(normalize_env_to_args "--data_block_builder" $DATA_BLOCK_BUILDER)
data_block_compressed_type=$(normalize_env_to_args "--data_block_compressed_type" $DATA_BLOCK_COMPRESSED_TYPE)

python -m fedlearner.data_join.cmd.data_join_worker_service \
    $PEER_ADDR \
    $MASTER_POD_NAMES \
    $INDEX \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    --listen_port=50051 \
    $raw_data_iter $compressed_type $read_ahead_size \
    $example_joiner $min_matching_window \
    $max_matching_window $data_block_dump_interval \
    $data_block_dump_threshold $example_id_dump_interval \
    $example_id_dump_threshold $example_id_batch_size \
    $max_flying_example_id $data_block_builder \
    $data_block_compressed_type $EAGER_MODE
