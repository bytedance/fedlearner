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
source ~/.env
export CUDA_VISIBLE_DEVICES=
cp /app/sgx/gramine/CI-Examples/tensorflow_io.py ./
source /app/deploy/scripts/hdfs_common.sh || true
source /app/deploy/scripts/pre_start_hook.sh || true
source /app/deploy/scripts/env_to_args.sh

LISTEN_PORT=50052
if [[ -n "${PORT1}" ]]; then
  LISTEN_PORT=${PORT1}
fi

if [[ -n "${CODE_KEY}" ]]; then
  pull_code ${CODE_KEY} $PWD
else
  pull_code ${CODE_TAR} $PWD
fi

cp /app/sgx/gramine/CI-Examples/tensorflow_io.py /gramine/leader
cp /app/sgx/gramine/CI-Examples/tensorflow_io.py /gramine/follower
source /app/deploy/scripts/sgx/enclave_env.sh

make_custom_env 4
source /root/start_aesm_service.sh

cd $EXEC_DIR
if [[ -z "${START_CPU_SN}" ]]; then
    START_CPU_SN=0
fi
if [[ -z "${END_CPU_SN}" ]]; then
    END_CPU_SN=3
fi

taskset -c $START_CPU_SN-$END_CPU_SN stdbuf -o0 gramine-sgx python -m fedlearner.trainer.parameter_server $POD_IP:${LISTEN_PORT}