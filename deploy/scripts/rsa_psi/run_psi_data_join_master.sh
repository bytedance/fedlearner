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

data_join_master_cmd=/app/deploy/scripts/data_join/run_data_join_master.sh

export RAW_DATA_SUB_DIR="portal_publish_dir/${APPLICATION_ID}_psi_preprocess"

# Reverse the role assignment for data join so that leader for PSI preprocessor
# becomes follower for data join. Data join's workers get their role from
# master so we don't need to do this for worker.
if [ $ROLE == "leader" ]; then
    export ROLE="follower"
else
    export ROLE="leader"
fi

${data_join_master_cmd}
