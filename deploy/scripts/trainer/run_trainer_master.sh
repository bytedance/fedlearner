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

epoch_num=$(normalize_env_to_args "--epoch_num" $EPOCH_NUM)
start_date=$(normalize_env_to_args "-start_date" $START_DATE)
end_date=$(normalize_env_to_args "-end_date" $END_DATE)
local_data_sources=$(normalize_env_to_args "-local_data_sources" $LOCAL_DATA_SOURCES)
local_data_start_dates=$(normalize_env_to_args "-local_data_start_dates" $LOCAL_DATA_START_DATES)
local_data_end_dates=$(normalize_env_to_args "-local_data_end_dates" $LOCAL_DATA_END_DATES)
shuffle_range=$(normalize_env_to_args "-shuffle_range" $SHUFFLE_RANGE)

python -m fedlearner.trainer_master.${ROLE}_tm \
    -app_id=$APPLICATION_ID \
    -data_source=$DATA_SOURCE \
    -p 50051 \
    $start_date $end_date $epoch_num $local_data_sources \
    $local_data_start_dates $local_data_end_dates \
    $shuffle_range \
    $ONLINE_TRAINING $SUFFLE_DATA_BLOCK
