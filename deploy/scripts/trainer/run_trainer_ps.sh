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

cp /app/sgx/gramine/CI-Examples/tensorflow_io.py ./
source /app/deploy/scripts/hdfs_common.sh || true
source /app/deploy/scripts/pre_start_hook.sh || true

LISTEN_PORT=50052
if [[ -n "${PORT1}" ]]; then
  LISTEN_PORT=${PORT1}
fi

python -m fedlearner.trainer.parameter_server $POD_IP:${LISTEN_PORT}
