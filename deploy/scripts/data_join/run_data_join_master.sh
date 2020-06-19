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

python -m fedlearner.data_join.cmd.prepare_launch_data_join_cli \
    --data_source_name=$DATA_SOURCE_NAME \
    --partition_num=$PARTITION_NUM \
    --start_time=$START_TIME \
    --end_time=$END_TIME \
    --negative_sampling_rate=$NEGATIVE_SAMPLING_RATE \
    --role=$ROLE \
    --data_block_dir=$DATA_BLOCK_DIR \
    --example_dump_dir=$EXAMPLE_DUMP_DIR \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    --raw_data_sub_dir=$RAW_DATA_SUB_DIR

python -m fedlearner.data_join.cmd.data_join_master_service \
    $PEER_ADDR \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    --listen_port=50051 \
    --data_source_name=$DATA_SOURCE_NAME
