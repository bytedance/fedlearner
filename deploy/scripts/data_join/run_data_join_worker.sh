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

python -m fedlearner.data_join.data_join_worker \
    $PEER_ADDR \
    $MASTER_POD_NAMES \
    $INDEX \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    --listen_port=50051 \
    --raw_data_iter=$RAW_DATA_ITER \
    --compressed_type=$COMPRESSED_TYPE \
    --example_joiner=$EXAMPLE_JOINER \
    --min_matching_window=$MIN_MATCHING_WINDOW \
    --max_matching_window=$MAX_MATCHING_WINDOW \
    --data_block_dump_interval=$DATA_BLOCK_DUMP_INTERVAL \
    --data_block_dump_threshold=$DATA_BLOCK_DUMP_THRESHOLD \
    --example_id_dump_interval=$EXAMPLE_ID_DUMP_INTERVAL \
    --example_id_dump_threshold=$EXAMPLE_ID_DUMP_THRESHOLD \
    --example_id_batch_size=$EXAMPLE_ID_BATCH_SIZE \
    --max_flying_example_id=$MAX_FLYING_EXAMPLE_ID \
    --data_block_builder=$DATA_BLOCK_BUILDER \
    $EAGER_MODE
