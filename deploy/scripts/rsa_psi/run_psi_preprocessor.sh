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

python -m fedlearner.data_join.rsa_psi.rsa_psi_preprocessor \
    --psi_role=$ROLE \
    --rsa_key_file_path=$RSA_KEY_PATH \
    --input_file_paths=$INPUT_FILE_PATHS \
    --output_file_dir=$OUTPUT_FILE_DIR \
    --leader_rsa_psi_signer_addr=$PEER_ADDR \
    --process_batch_size=$PROCESS_BATCH_SIZE \
    --max_flying_item=$MAX_FLYING_ITEM \
    --offload_processor_number=$OFFLOAD_PROCSSOR_NUMBER \
    --partition_id=$INDEX \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    --raw_data_publish_dir=$RAW_DATA_PUBLISH_DIR
