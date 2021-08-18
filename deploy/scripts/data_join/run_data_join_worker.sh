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

raw_data_iter=$(normalize_env_to_args "--raw_data_iter" $RAW_DATA_ITER)
compressed_type=$(normalize_env_to_args "--compressed_type" $COMPRESSED_TYPE)
read_ahead_size=$(normalize_env_to_args "--read_ahead_size" $READ_AHEAD_SIZE)
read_batch_size=$(normalize_env_to_args "--read_batch_size" $READ_BATCH_SIZE)
example_joiner=$(normalize_env_to_args "--example_joiner" $EXAMPLE_JOINER)
min_matching_window=$(normalize_env_to_args "--min_matching_window" $MIN_MATCHING_WINDOW)
max_matching_window=$(normalize_env_to_args "--max_matching_window" $MAX_MATCHING_WINDOW)
data_block_dump_interval=$(normalize_env_to_args "--data_block_dump_interval" $DATA_BLOCK_DUMP_INTERVAL)
data_block_dump_threshold=$(normalize_env_to_args "--data_block_dump_threshold" $DATA_BLOCK_DUMP_THRESHOLD)
example_id_dump_interval=$(normalize_env_to_args "--example_id_dump_interval" $EXAMPLE_ID_DUMP_INTERVAL)
example_id_dump_threshold=$(normalize_env_to_args "--example_id_dump_threshold" $EXAMPLE_ID_DUMP_THRESHOLD)
data_block_builder=$(normalize_env_to_args "--data_block_builder" $DATA_BLOCK_BUILDER)
data_block_compressed_type=$(normalize_env_to_args "--data_block_compressed_type" $DATA_BLOCK_COMPRESSED_TYPE)
kvstore_type=$(normalize_env_to_args '--kvstore_type' $KVSTORE_TYPE)
max_conversion_delay=$(normalize_env_to_args '--max_conversion_delay' $MAX_CONVERSION_DELAY)
enable_negative_example_generator=$(normalize_env_to_args '--enable_negative_example_generator' $ENABLE_NEGATIVE_EXAMPLE_GENERATOR)
negative_sampling_rate=$(normalize_env_to_args '--negative_sampling_rate' $NEGATIVE_SAMPLING_RATE)
optional_fields=$(normalize_env_to_args '--optional_fields' $OPTIONAL_FIELDS)

join_expr=$(normalize_env_to_args '--join_expr' ${JOIN_EXPR})
negative_sampling_filter_expr=$(normalize_env_to_args '--negative_sampling_filter_expr' ${NEGATIVE_SAMPLING_FILTER_EXPR})
raw_data_cache_type=$(normalize_env_to_args '--raw_data_cache_type' ${RAW_DATA_CACHE_TYPE})
join_key_mapper=$(normalize_env_to_args '--join_key_mapper' ${JOIN_KEY_MAPPER})

if [ -n "$JOIN_KEY_MAPPER" ]; then
    IFS='=' read -r -a mapper <<< "$JOIN_KEY_MAPPER"
    echo "${mapper[0]}"
    pull_code "${mapper[1]}" /app/fedlearner/data_join/key_mapper/impl
    join_key_mapper=$(normalize_env_to_args '--join_key_mapper' "${mapper[0]}")
fi

python -m fedlearner.data_join.cmd.data_join_worker_service \
    $PEER_ADDR \
    $MASTER_POD_NAMES \
    $INDEX \
    --listen_port=50051 \
    $raw_data_iter $compressed_type $read_ahead_size $read_batch_size \
    $example_joiner $min_matching_window $max_matching_window \
    $data_block_dump_interval $data_block_dump_threshold \
    $example_id_dump_interval $example_id_dump_threshold \
    $data_block_builder $data_block_compressed_type \
    $kvstore_type $max_conversion_delay \
    $enable_negative_example_generator $negative_sampling_rate \
    $join_expr $join_key_mapper $optional_fields $raw_data_cache_type $negative_sampling_filter_expr
