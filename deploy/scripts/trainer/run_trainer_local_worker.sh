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
export MODEL_NAME=${APPLICATION_ID}

source /app/deploy/scripts/hdfs_common.sh || true
source /app/deploy/scripts/pre_start_hook.sh || true
source /app/deploy/scripts/env_to_args.sh

if [[ -n "${CODE_KEY}" ]]; then
  pull_code ${CODE_KEY} $PWD
else
  pull_code ${CODE_TAR} $PWD
fi

cd ${ROLE}

mode=$(normalize_env_to_args "--mode" "$MODE")
sparse_estimator=$(normalize_env_to_args "--sparse-estimator" "$SPARSE_ESTIMATOR")
batch_size=$(normalize_env_to_args "--batch-size" "$BATCH_SIZE")
learning_rate=$(normalize_env_to_args "--learning-rate" "$LEARNING_RATE")
extra_params=$(normalize_env_to_args "--extra-params" "$EXTRA_PARAMS")

if [ -n "$CLUSTER_SPEC" ]; then
  # get master address from clusteSpec["master"]
  MASTER_HOST=`python -c "
import json
cluster_spec = json.loads('$CLUSTER_SPEC')['clusterSpec']
if 'Master' in cluster_spec:
  print(cluster_spec['Master'][0].split(':')[0])
"`
  NUM_WORKER=`python -c """
import json
cluster_spec = json.loads('$CLUSTER_SPEC')['clusterSpec']
print(len(cluster_spec.get('Worker', [])))
"""`

  # rewrite tensorflow ClusterSpec for compatibility
  # master port 50051 is used for fedlearner master server, so rewrite to 50052
  # worker port 50051 is used for fedlearner worker server, so rewrite to 50052
  CLUSTER_SPEC=`python -c """
import json
def rewrite_port(address, old, new):
  (host, port) = address.rsplit(':', 1)
  if port == old:
    return host + ':' + new
  return address

cluster_spec = json.loads('$CLUSTER_SPEC')['clusterSpec']
for i, ps in enumerate(cluster_spec.get('PS', [])):
  cluster_spec['PS'][i] = rewrite_port(ps, '50051', '50052')
for i, master in enumerate(cluster_spec.get('Master', [])):
  cluster_spec['Master'][i] = rewrite_port(master, '50051', '50052')
for i, worker in enumerate(cluster_spec.get('Worker', [])):
  cluster_spec['Worker'][i] = rewrite_port(worker, '50051', '50052')
if 'LocalWorker' in cluster_spec:
  for i, worker in enumerate(cluster_spec.get('LocalWorker', [])):
    cluster_spec['Worker'].append(rewrite_port(worker, '50051', '50052'))
  del cluster_spec['LocalWorker']
print(json.dumps({'clusterSpec': cluster_spec}))
"""`
fi

server_port=$(normalize_env_to_args "--server-port" "$PORT1")

WORKER_RANK=`python -c "print($INDEX + $NUM_WORKER)"`

python main.py --worker \
    --local-worker \
    --application-id="$APPLICATION_ID" \
    --master-addr="$MASTER_HOST:50051" \
    --cluster-spec="$CLUSTER_SPEC" \
    --worker-rank="$WORKER_RANK" \
    $server_port $mode $batch_size \
    $sparse_estimator $learning_rate $extra_params
