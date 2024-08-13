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

WORKER_REPLICAS=`python -c 'import json, os; print(len(json.loads(os.environ["CLUSTER_SPEC"])["clusterSpec"]["Worker"]))'`

echo "${WORKER_REPLICAS:?Need to set WORKER_REPLICAS non-empty}"
echo "${INDEX:?Need to set INDEX non-empty}"
if [ "$((WORKER_REPLICAS % 2))" -ne "0" ]; then
  echo "Error: WORKER_REPLICAS should be the multiplies of 2."
  exit 1
fi
if [ $INDEX -lt $((WORKER_REPLICAS / 2)) ]; then
  psi_preprocessor_cmd=/app/deploy/scripts/rsa_psi/run_psi_preprocessor.sh
  exec ${psi_preprocessor_cmd} &
  echo "launched run psi preprocessor"
else
  join_worker_cmd=/app/deploy/scripts/data_join/run_data_join_worker.sh
  exec ${join_worker_cmd} &
  echo "launched data join worker"
fi
echo "waiting for finished"
wait
