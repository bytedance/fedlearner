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

if [ -z "$INPUT_BASE_DIR$INPUT_FILE_PATHS" ]
then
    echo "no input files or directory for psi preprocessor"
    exit -1
fi

preprocessor_name=$(normalize_env_to_args "--preprocessor_name" $NAME)
input_file_paths=$(normalize_env_to_args "--input_file_paths" $INPUT_FILE_PATHS)
if [ -z "$INPUT_BASE_DIR" ]
then
    input_dir=""
else
    input_dir="--input_dir=$INPUT_BASE_DIR/partition_`echo $INDEX|awk '{printf("%04d\n",$0)}'`"
fi
input_file_subscribe_dir=$(normalize_env_to_args "--input_file_subscribe_dir" $INPUT_FILE_SUBSCRIBE_DIR)
leader_rsa_psi_signer_addr=$(normalize_env_to_args "--leader_rsa_psi_signer_addr" $PEER_ADDR)
max_flying_item=$(normalize_env_to_args "--max_flying_item" $MAX_FLYING_ITEM)
offload_processor_number=$(normalize_env_to_args "--offload_processor_number" $OFFLOAD_PROCESSOR_NUMBER)
process_batch_size=$(normalize_env_to_args "--process_batch_size" $PSI_PROCESS_BATCH_SIZE)
max_flying_sign_batch=$(normalize_env_to_args "--max_flying_sign_batch" $MAX_FLYING_SIGNED_BATCH)
max_flying_sign_rpc=$(normalize_env_to_args "--max_flying_sign_rpc" $MAX_FLYING_SIGN_RPC)
sign_rpc_timeout_ms=$(normalize_env_to_args "--sign_rpc_timeout_ms" $SIGN_RPC_TIMEOUT_MS)
stub_fanout=$(normalize_env_to_args "--stub_fanout" $STUB_FANOUT)
rpc_thread_pool_size=$(normalize_env_to_args "--rpc_thread_pool_size" $RPC_THREAD_POOL_SIZE)
slow_sign_threshold=$(normalize_env_to_args "--slow_sign_threshold" $SLOW_SIGN_THRESHOLD)
sort_run_merger_read_ahead_buffer=$(normalize_env_to_args "--sort_run_merger_read_ahead_buffer" $SORT_RUN_MERGER_READ_AHEAD_BUFFER)

python -m fedlearner.data_join.cmd.rsa_psi_preprocessor_cli \
    --psi_role=$ROLE \
    --rsa_key_path=$RSA_KEY_PATH \
    --rsa_key_pem="$RSA_KEY_PEM" \
    --output_file_dir=$OUTPUT_FILE_DIR \
    --raw_data_publish_dir=$RAW_DATA_PUBLISH_DIR \
    --partition_id=$INDEX \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    $preprocessor_name $input_file_paths $input_dir $input_file_subscribe_dir \
    $max_flying_item $max_flying_sign_batch $offload_processor_number \
    $slow_sign_threshold $sort_run_merger_read_ahead_buffer \
    $leader_rsa_psi_signer_addr $max_flying_sign_rpc $sign_rpc_timeout_ms \
    $stub_fanout $rpc_thread_pool_size $process_batch_size $RPC_SYNC_MODE
