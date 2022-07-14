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

source /app/deploy/scripts/pre_start_hook.sh || true

psi_preprocessor_cmd=/app/deploy/scripts/rsa_psi/run_psi_preprocessor.sh
data_join_worker_cmd=/app/deploy/scripts/data_join/run_data_join_worker.sh

echo "launch ras psi preprocessor at front ground"
${psi_preprocessor_cmd}
echo "ras psi preprocessor run finished"

TCP_MSL=60
if [ -f "/proc/sys/net/ipv4/tcp_fin_timeout" ]
then
  TCP_MSL=`cat /proc/sys/net/ipv4/tcp_fin_timeout`
fi
SLEEP_TM=$((TCP_MSL * 3))
echo "sleep 3msl($SLEEP_TM) to make sure tcp state at CLOSED"
sleep $SLEEP_TM

echo "launch data join worker"
export RAW_DATA_ITER=$PSI_OUTPUT_BUILDER
export COMPRESSED_TYPE=$PSI_OUTPUT_BUILDER_COMPRESSED_TYPE
${data_join_worker_cmd}
echo "data join worker finished"
