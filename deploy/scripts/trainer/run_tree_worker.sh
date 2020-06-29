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

NUM_WORKERS=`python -c 'import json, os; print(len(json.loads(os.environ["CLUSTER_SPEC"])["clusterSpec"]["Worker"]))'`

mode=$(normalize_env_to_args "--mode" $MODE)
data_path=$(normalize_env_to_args "--data-path" $DATA_PATH)
validation_data_path=$(normalize_env_to_args "--validation-data-path" $VALIDATION_DATA_PATH)
no_data=$(normalize_env_to_args "--no-data" $NO_DATA)
file_ext=$(normalize_env_to_args "--file-ext" $FILE_EXT)
load_model_path=$(normalize_env_to_args "--load-model-path" $LOAD_MODEL_PATH)
export_path=$(normalize_env_to_args "--export-path" $EXPORT_PATH)
checkpoint_path=$(normalize_env_to_args "--checkpoint-path" $CHECKPOINT_PATH)
output_path=$(normalize_env_to_args "--output-path" $OUTPUT_PATH)
verbosity=$(normalize_env_to_args "--verbosity" $VERBOSITY)
learning_rate=$(normalize_env_to_args "--learning-rate" $LEARNING_RATE)
max_iters=$(normalize_env_to_args "--max-iters" $MAX_ITERS)
max_depth=$(normalize_env_to_args "--max-depth" $MAX_DEPTH)
l2_regularization=$(normalize_env_to_args "--l2-regularization" $L2_REGULARIZATION)
max_bins=$(normalize_env_to_args "--max-bins" $MAX_BINS)
num_parallel=$(normalize_env_to_args "--num-parallel" $NUM_PARALELL)
verify_example_ids=$(normalize_env_to_args "--verify-example-ids" $VERIFY_EXAMPLE_IDS)
ignore_fields=$(normalize_env_to_args "--ignore-fields" $IGNORE_FIELDS)
cat_fields=$(normalize_env_to_args "--cat-fields" $CAT_FIELDS)
use_streaming=$(normalize_env_to_args "--use-streaming" $USE_STREAMING)
send_scores_to_follower=$(normalize_env_to_args "--send-scores-to-follower" $SEND_SCORES_TO_FOLLOWER)


python -m fedlearner.model.tree.trainer \
    "${ROLE}" \
    --local-addr="$POD_IP:50051" \
    --peer-addr="$PEER_ADDR" \
    --num-workers="$NUM_WORKERS" \
    --worker-rank="$WORKER_RANK" \
    --application-id="$APPLICATION_ID" \
    $mode $data_path $validation_data_path \
    $no_data $file_ext $load_model_path \
    $export_path $checkpoint_path $output_path \
    $verbosity $learning_rate $max_iters \
    $max_depth $l2_regularization $max_bins \
    $num_parallel $verify_example_ids $ignore_fields \
    $cat_fields $use_streaming $send_scores_to_follower
