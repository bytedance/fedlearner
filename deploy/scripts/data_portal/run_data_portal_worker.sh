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

merge_buffer_size=$(normalize_env_to_args "--merge_buffer_size" $MERGE_BUFFER_SIZE)
writer_buffer_size=$(normalize_env_to_args "--write_buffer_size" $WRITE_BUFFER_SIZE)
input_data_file_iter=$(normalize_env_to_args "--input_data_file_iter" $INPUT_DATA_FORMAT)
output_data_file_type=$(normalize_env_to_args "--output_data_file_type" $OUTPUT_DATA_FORMAT)
compressed_type=$(normalize_env_to_args "--compressed_type" $COMPRESSED_TYPE)


python -m fedlearner.data_join.cmd.data_portal_worker_cli \
  --master_addr=$MASTER_POD_NAMES \
  --rank_id=$INDEX \
  --etcd_name=$ETCD_NAME \
  --etcd_addrs=$ETCD_ADDRS \
  --etcd_base_dir=$ETCD_BASE_DIR \
  --batch_size=$BATCH_SIZE \
  --max_flying_item=$MAX_FLYING_ITEM \
  $merge_buffer_size $write_buffer_size \
  $input_data_file_iter $compressed_type \
  $output_data_file_type
  

