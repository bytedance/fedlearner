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

slow_sign_threshold=$(normalize_env_to_args "--slow_sign_threshold" $SLOW_SIGN_THRESHOLD)
worker_num=$(normalize_env_to_args "--worker_num" $WORKER_NUM)
signer_offload_processor_number=$(normalize_env_to_args "--signer_offload_processor_number" $SIGNER_OFFLOAD_PROCESSOR_NUMBER)

# Turn off display to avoid RSA_KEY_PEM showing in log
set +x

cp /app/sgx/gramine/CI-Examples/tensorflow_io.py ./
unset HTTPS_PROXY https_proxy http_proxy ftp_proxy

python -m fedlearner.data_join.cmd.rsa_psi_signer_service \
    --listen_port=50051 \
    --rsa_private_key_path="$RSA_PRIVATE_KEY_PATH" \
    --rsa_privet_key_pem="$RSA_KEY_PEM" \
    $slow_sign_threshold $worker_num $signer_offload_processor_number
