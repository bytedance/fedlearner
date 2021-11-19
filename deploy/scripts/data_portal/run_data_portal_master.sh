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
source /app/deploy/scripts/pre_start_hook.sh || true
source /app/deploy/scripts/env_to_args.sh

input_file_wildcard=$(normalize_env_to_args "--input_file_wildcard" "$FILE_WILDCARD")
kvstore_type=$(normalize_env_to_args '--kvstore_type' $KVSTORE_TYPE)
files_per_job_limit=$(normalize_env_to_args '--files_per_job_limit' $FILES_PER_JOB_LIMIT)
start_date=$(normalize_env_to_args '--start_date' $START_DATE)
end_date=$(normalize_env_to_args '--end_date' $END_DATE)

python -m fedlearner.data_join.cmd.data_portal_master_service \
    --listen_port=50051 \
    --data_portal_name=$DATA_PORTAL_NAME \
    --data_portal_type=$DATA_PORTAL_TYPE \
    --output_partition_num=$OUTPUT_PARTITION_NUM \
    --input_base_dir=$INPUT_BASE_DIR \
    --output_base_dir=$OUTPUT_BASE_DIR \
    --raw_data_publish_dir=$RAW_DATA_PUBLISH_DIR \
    $input_file_wildcard $LONG_RUNNING $CHECK_SUCCESS_TAG \
    $kvstore_type $SINGLE_SUBFOLDER $files_per_job_limit \
    $start_date $end_date
