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

UPLOAD_DIR=$OUTPUT_BASE_DIR/upload
${HADOOP_HOME}/bin/hadoop fs -mkdir -p $UPLOAD_DIR
spark_entry_script="fedlearner/data_join/raw_data/raw_data.py"
${HADOOP_HOME}/bin/hadoop fs -put -f $spark_entry_script $UPLOAD_DIR

input_file_wildcard=$(normalize_env_to_args "--input_file_wildcard" $FILE_WILDCARD)
kvstore_type=$(normalize_env_to_args '--kvstore_type' $KVSTORE_TYPE)
files_per_job_limit=$(normalize_env_to_args '--files_per_job_limit' $FILES_PER_JOB_LIMIT)
start_date=$(normalize_env_to_args '--start_date' $START_DATE)
end_date=$(normalize_env_to_args '--end_date' $END_DATE)
output_type=$(normalize_env_to_args '--output_type' $OUTPUT_TYPE)
data_source_name=$(normalize_env_to_args '--data_source_name' $DATA_SOURCE_NAME)
data_block_dump_threshold=$(normalize_env_to_args '--data_block_dump_threshold' $DATA_BLOCK_DUMP_THRESHOLD)
spark_driver_cores=$(normalize_env_to_args '--spark_driver_cores' $SPARK_DRIVER_CORES)
spark_driver_memory=$(normalize_env_to_args '--spark_driver_memory' $SPARK_DRIVER_MEMORY)
spark_executor_cores=$(normalize_env_to_args '--spark_executor_cores' $SPARK_EXECUTOR_CORES)
spark_executor_memory=$(normalize_env_to_args '--spark_executor_memory' $SPARK_EXECUTOR_MEMORY)
spark_executor_instances=$(normalize_env_to_args '--spark_executor_instances' $SPARK_EXECUTOR_INSTANCES)

python -m fedlearner.data_join.cmd.raw_data_cli \
    --data_portal_name=$DATA_PORTAL_NAME \
    --data_portal_type=$DATA_PORTAL_TYPE \
    --output_partition_num=$OUTPUT_PARTITION_NUM \
    --input_base_dir=$INPUT_BASE_DIR \
    --output_base_dir=$OUTPUT_BASE_DIR \
    --raw_data_publish_dir=$RAW_DATA_PUBLISH_DIR \
    --upload_dir=$UPLOAD_DIR \
    $input_file_wildcard $LONG_RUNNING $CHECK_SUCCESS_TAG \
    $SINGLE_SUBFOLDER $files_per_job_limit $output_type \
    $data_source_name $data_block_dump_threshold \
    $spark_driver_cores $spark_driver_memory \
    $spark_executor_cores $spark_executor_memory $spark_executor_instances
