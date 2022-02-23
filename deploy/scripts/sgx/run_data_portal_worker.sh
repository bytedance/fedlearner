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

cp /app/sgx/gramine/CI-Examples/tensorflow_io.py ./
cp /app/sgx/token/* ./
unset HTTPS_PROXY https_proxy http_proxy ftp_proxy

function get_env() {
    gramine-sgx-get-token -s python.sig -o /dev/null | grep $1 | awk -F ":" '{print $2}' | xargs
}

function make_custom_env() {
    export DEBUG=0
    export CUDA_VISIBLE_DEVICES=""
    export DNNL_VERBOSE=0
    export GRPC_VERBOSITY=ERROR
    export GRPC_POLL_STRATEGY=epoll1
    export TF_CPP_MIN_LOG_LEVEL=1
    export TF_GRPC_SGX_RA_TLS_ENABLE=on
    export FL_GRPC_SGX_RA_TLS_ENABLE=on
    export TF_DISABLE_MKL=0
    export TF_ENABLE_MKL_NATIVE_FORMAT=1
    export parallel_num_threads=$1
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    export GRPC_SERVER_CHANNEL_THREADS=4
    export KMP_SETTINGS=1
    export KMP_BLOCKTIME=0
    export MR_ENCLAVE=`get_env mr_enclave`
    export MR_SIGNER=`get_env mr_signer`
    export ISV_PROD_ID=`get_env isv_prod_id`
    export ISV_SVN=`get_env isv_svn`
    # network proxy
    unset http_proxy https_proxy
    jq ' .sgx_mrs[0].mr_enclave = ''"'`get_env mr_enclave`'" | .sgx_mrs[0].mr_signer = ''"'`get_env mr_signer`'" ' \
        $GRPC_PATH/examples/dynamic_config.json > ./dynamic_config.json
}

make_custom_env 4

taskset -c 0-3 stdbuf -o0 gramine-sgx python -m fedlearner.data_join.cmd.data_portal_worker_cli \
  --rank_id=$INDEX \
  --master_addr=$MASTER_POD_NAMES \
  $input_data_file_iter $compressed_type $read_ahead_size $read_batch_size \
  $output_builder $builder_compressed_type \
  $batch_size $kvstore_type $memory_limit_ratio \
  $optional_fields $input_data_validation_ratio

