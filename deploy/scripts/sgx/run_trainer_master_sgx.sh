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

mode=$(normalize_env_to_args "--mode" "$MODE")
sparse_estimator=$(normalize_env_to_args "--sparse-estimator" "$SPARSE_ESTIMATOR")
save_checkpoint_steps=$(normalize_env_to_args "--save-checkpoint-steps" "$SAVE_CHECKPOINT_STEPS")
save_checkpoint_secs=$(normalize_env_to_args "--save-checkpoint-secs" "$SAVE_CHECKPOINT_SECS")
summary_save_steps=$(normalize_env_to_args "--summary-save-steps" "$SUMMARY_SAVE_STEPS")
summary_save_secs=$(normalize_env_to_args "--summary-save-secs" "$SUMMARY_SAVE_SECS")
epoch_num=$(normalize_env_to_args "--epoch-num" $EPOCH_NUM)
start_date=$(normalize_env_to_args "--start-date" $START_DATE)
end_date=$(normalize_env_to_args "--end-date" $END_DATE)
extra_params=$(normalize_env_to_args "--extra-params" "$EXTRA_PARAMS")
export_model=$(normalize_env_to_args "--export-model" $EXPORT_MODEL)
shuffle=$(normalize_env_to_args "--shuffle" $SUFFLE_DATA_BLOCK)
shuffle_in_day=$(normalize_env_to_args "--shuffle-in-day" $SHUFFLE_IN_DAY)
local_data_source=$(normalize_env_to_args "--local-data-source" $LOCAL_DATA_SOURCE)
local_data_path=$(normalize_env_to_args "--local-data-path" $LOCAL_DATA_PATH)
local_start_date=$(normalize_env_to_args "--local-start-date" $LOCAL_START_DATE)
local_end_date=$(normalize_env_to_args "--local-end-date" $LOCAL_END_DATE)

if [ -n "$CHECKPOINT_PATH" ]; then
    checkpoint_path="--checkpoint-path=$CHECKPOINT_PATH"
else
    checkpoint_path="--checkpoint-path=$OUTPUT_BASE_DIR/checkpoints"
fi
load_checkpoint_path=$(normalize_env_to_args "--load-checkpoint-path" "$LOAD_CHECKPOINT_PATH")
load_checkpoint_filename=$(normalize_env_to_args "--load-checkpoint-filename" "$LOAD_CHECKPOINT_FILENAME")
load_checkpoint_filename_with_path=$(normalize_env_to_args "--load-checkpoint-filename-with-path" "$LOAD_CHECKPOINT_FILENAME_WITH_PATH")

if [[ -n "$EXPORT_PATH" ]]; then
    export_path="--export-path=$EXPORT_PATH"
else
    export_path="--export-path=$OUTPUT_BASE_DIR/exported_models"
fi

if [ -n "$CLUSTER_SPEC" ]; then
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

if [[ -n "${CODE_KEY}" ]]; then
  pull_code ${CODE_KEY} $PWD
else
  pull_code ${CODE_TAR} $PWD
fi
cd ${ROLE}
cp /app/sgx/gramine/CI-Examples/tensorflow_io.py ./
source /app/deploy/scripts/sgx/enclave_env.sh
cp /app/sgx/token/* ./
unset HTTPS_PROXY https_proxy http_proxy ftp_proxy

make_custom_env 4
source /root/start_aesm_service.sh

LISTEN_PORT=50051
if [[ -n "${PORT0}" ]]; then
  LISTEN_PORT=${PORT0}
fi

server_port=$(normalize_env_to_args "--server-port" "$PORT1")

if [[ -z "${START_CPU_SN}" ]]; then
    START_CPU_SN=0
fi
if [[ -z "${END_CPU_SN}" ]]; then
    END_CPU_SN=3
fi

taskset -c $START_CPU_SN-$END_CPU_SN stdbuf -o0 gramine-sgx python main.py --master \
    --application-id=$APPLICATION_ID \
    --data-source=$DATA_SOURCE \
    --data-path=$DATA_PATH \
    --data-path-wildcard=$DATA_PATH_WILDCARD \
    --master-addr=0.0.0.0:${LISTEN_PORT} \
    --cluster-spec="$CLUSTER_SPEC" \
    $server_port \
    $checkpoint_path $load_checkpoint_path \
    $load_checkpoint_filename $load_checkpoint_filename_with_path \
    $export_path \
    $mode $sparse_estimator \
    $save_checkpoint_steps $save_checkpoint_secs \
    $summary_save_steps $summary_save_secs \
    $local_data_source $local_data_path $local_start_date \
    $local_end_date $epoch_num $start_date $end_date \
    $shuffle $shuffle_in_day $extra_params $export_model
