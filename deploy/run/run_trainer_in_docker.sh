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

CUR_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH=$PYTHONPATH:$CUR_DIR/../..

code_url="https://github.com/rapmetal/fedlearner_models/releases/download/${RELEASE_TAG}/${RELEASE_PKG}.zip"
wget $code_url
unzip "${RELEASE_PKG}.zip"
echo "CUDA_VISIBLE_DEVICES=\"\" python ${RELEASE_PKG}/${ROLE}.py --cluster-spec=$CLUSTER_SPEC --tf-addr=$POD_IP:50052 --local-addr=$POD_IP:50051 --worker-rank=$WORKER_RANK --peer-addr=$REMOTE_IP"
CUDA_VISIBLE_DEVICES="" python "${RELEASE_PKG}/${ROLE}.py" --cluster-spec=$CLUSTER_SPEC --tf-addr=$POD_IP:50052 --local-addr=$POD_IP:50051 --worker-rank=$WORKER_RANK --peer-addr=$REMOTE_IP
