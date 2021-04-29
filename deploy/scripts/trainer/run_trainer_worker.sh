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
verbosity=$(normalize_env_to_args "--verbosity" "$VERBOSITY")
save_checkpoint_steps=$(normalize_env_to_args "--save-checkpoint-steps" "$SAVE_CHECKPOINT_STEPS")
save_checkpoint_secs=$(normalize_env_to_args "--save-checkpoint-secs" "$SAVE_CHECKPOINT_SECS")
sparse_estimator=$(normalize_env_to_args "--sparse-estimator" "$SPARSE_ESTIMATOR")
summary_save_steps=$(normalize_env_to_args "--summary-save-steps" "$SUMMARY_SAVE_STEPS")
batch_size=$(normalize_env_to_args "--batch-size" "$BATCH_SIZE")
learning_rate=$(normalize_env_to_args "--learning-rate" "$LEARNING_RATE")
local_data_sources=$(normalize_env_to_args "--local_data_sources" $LOCAL_DATA_SOURCES)
profiling_step=$(normalize_env_to_args "--profiling_step" $PROFILING_STEP)

if [ -n "$CHECKPOINT_PATH" ]; then
    checkpoint_path="$CHECKPOINT_PATH"
else
    checkpoint_path="$OUTPUT_BASE_DIR/checkpoints"
fi
load_checkpoint_filename=$(normalize_env_to_args "--load-checkpoint-filename" "$LOAD_CHECKPOINT_FILENAME")
load_checkpoint_filename_with_path=$(normalize_env_to_args "--load-checkpoint-filename-with-path" "$LOAD_CHECKPOINT_FILENAME_WITH_PATH")

if [[ -n "$LOAD_CHECKPOINT_FROM" ]] && (( $WORKER_RANK == 0 )); then
    python -c "
try:
    import tensorflow.compat.v1 as tf
except ImportError:
    import tensorflow as tf
import tensorflow_io
src = '${STORAGE_ROOT_PATH}/job_output/${LOAD_CHECKPOINT_FROM}/checkpoints'
dst = '${checkpoint_path}'
for root, _, files in tf.io.gfile.walk(src):
    root = root[len(src):]
    print('makedirs', dst + '/' + root)
    tf.io.gfile.makedirs(dst + '/' + root)
    for f in files:
        src_file = src + '/' + root + '/' + f
        dst_file = dst + '/' + root + '/' + f
        print('copy', src_file, 'to', dst_file)
        tf.io.gfile.copy(src_file, dst_file)
    "
fi

if [[ -n "$EXPORT_PATH" ]]; then
    export_path="$EXPORT_PATH"
else
    export_path="$OUTPUT_BASE_DIR/exported_models"
fi


python main.py \
    --data-path="$DATA_PATH" \
    --application-id="$APPLICATION_ID" \
    --cluster-spec="$CLUSTER_SPEC" \
    --tf-addr="$POD_IP:50052" \
    --local-addr="$POD_IP:50051" \
    --worker-rank="$WORKER_RANK" \
    --peer-addr="$PEER_ADDR" \
    --checkpoint-path=$checkpoint_path \
    --export-path=$export_path \
    $mode $verbosity \
    $save_checkpoint_steps $sparse_estimator $summary_save_steps \
    $save_checkpoint_secs $batch_size $learning_rate \
    $local_data_sources \
    $load_checkpoint_filename \
    $load_checkpoint_filename_with_path \
    $profiling_step
