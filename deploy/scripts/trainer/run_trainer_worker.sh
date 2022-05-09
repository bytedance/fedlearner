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

# When the WORKER_GROUPS is "2,4", this script would update the WORKER_RANK
# to the worker's index within their own group, e.g.
#
# + WORKER_RANK 0 -> 0
# + WORKER_RANK 1 -> 1
# + WORKER_RANK 2 -> 0
# + WORKER_RANK 3 -> 1
# + WORKER_RANK 4 -> 2
# + WORKER_RANK 5 -> 3
#
if [ -n "$WORKER_GROUPS" ]; then
IFS=',' read -ra WORKER_GROUPS <<< "$WORKER_GROUPS"
for i in "${WORKER_GROUPS[@]}"; do
    if (( $WORKER_RANK - $i < 0 )); then
        break
    else
        WORKER_RANK=$( expr $WORKER_RANK - $i )
    fi
done
fi

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
  LOCAL_WORKER_RANK=$((WORKER_RANK+NUM_WORKER))
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
num_worker = len(cluster_spec.get('Worker', []))
for i in range(num_worker):
  cluster_spec['Worker'].append(rewrite_port(cluster_spec['Worker'][i], '50052',
                                             str(50052+10000)))
print(json.dumps({'clusterSpec': cluster_spec}))
"""`
fi

LISTEN_PORT=50051
if [[ -n "${PORT0}" ]]; then
  LISTEN_PORT=${PORT0}
fi

server_port=$(normalize_env_to_args "--server-port" "$PORT1")

python main.py --worker \
    --is-local-worker \
    --application-id="$APPLICATION_ID" \
    --master-addr="$MASTER_HOST:50051" \
    --cluster-spec="$CLUSTER_SPEC" \
    --worker-rank="$LOCAL_WORKER_RANK" \
    $mode $batch_size \
    $sparse_estimator $learning_rate > local_worker.log 2>&1 &
local_worker_pid=$!

echo python main.py --worker \
    --application-id="$APPLICATION_ID" \
    --master-addr="$MASTER_HOST:50051" \
    --cluster-spec="$CLUSTER_SPEC" \
    --local-addr="$POD_IP:${LISTEN_PORT}" \
    --peer-addr="$PEER_ADDR" \
    --worker-rank="$WORKER_RANK" \
    $server_port $mode $batch_size \
    $sparse_estimator $learning_rate

wait $local_worker_pid
