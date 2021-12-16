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

psi_data_join_leader_worker_cmd=/app/deploy/scripts/data_join/run_psi_data_join_leader_worker_v2.sh
psi_data_join_follower_worker_cmd=/app/deploy/scripts/data_join/run_psi_data_join_follower_worker_v2.sh

export INPUT_FILE_SUBSCRIBE_DIR=$RAW_DATA_SUB_DIR
export RAW_DATA_PUBLISH_DIR="portal_publish_dir/${APPLICATION_ID}_psi_preprocess"
export MASTER_POD_NAMES=`python -c 'import json, os; print(json.loads(os.environ["CLUSTER_SPEC"])["clusterSpec"]["Master"][0])'`

if [ $ROLE == "leader" ]; then
    ${psi_data_join_leader_worker_cmd}
else
    ${psi_data_join_follower_worker_cmd}
fi
