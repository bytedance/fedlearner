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
export MODEL_NAME=${APPLICATION_ID}

LISTEN_PORT=50051
if [[ -n "${PORT0}" ]]; then
  LISTEN_PORT=${PORT0}
fi

echo $LISTEN_PORT > /pod-data/listen_port

cp /app/sgx/gramine/CI-Examples/tensorflow_io.py ./
source /app/deploy/scripts/hdfs_common.sh || true
source /app/deploy/scripts/pre_start_hook.sh || true
source /app/deploy/scripts/env_to_args.sh

PEER_ADDR="localhost:${PROXY_LOCAL_PORT}"

if [[ -n "${CODE_KEY}" ]]; then
  pull_code ${CODE_KEY} $PWD
else
  pull_code ${CODE_TAR} $PWD
fi

cp /app/sgx/gramine/CI-Examples/tensorflow_io.py /gramine/follower/
cp /app/sgx/gramine/CI-Examples/tensorflow_io.py /gramine/leader/
source /app/deploy/scripts/sgx/enclave_env.sh

unset HTTPS_PROXY https_proxy http_proxy ftp_proxy

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

make_custom_env 4
source /root/start_aesm_service.sh

server_port=$(normalize_env_to_args "--server-port" "$PORT1")

cd $EXEC_DIR
if [[ -z "${START_CPU_SN}" ]]; then
    START_CPU_SN=0
fi
if [[ -z "${END_CPU_SN}" ]]; then
    END_CPU_SN=3
fi

taskset -c $START_CPU_SN-$END_CPU_SN stdbuf -o0 gramine-sgx python /gramine/$ROLE/main.py --worker \
    --application-id="$APPLICATION_ID" \
    --master-addr="$MASTER_HOST:50051" \
    --cluster-spec="$CLUSTER_SPEC" \
    --local-addr="$POD_IP:${LISTEN_PORT}" \
    --peer-addr="$PEER_ADDR" \
    --worker-rank="$INDEX" \
    $server_port $mode $batch_size \
    $sparse_estimator $learning_rate