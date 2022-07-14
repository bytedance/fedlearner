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

source /app/deploy/scripts/pre_start_hook.sh || true

psi_signer_cmd=/app/deploy/scripts/rsa_psi/run_rsa_psi_signer.sh
psi_preprocessor_cmd=/app/deploy/scripts/rsa_psi/run_psi_preprocessor.sh 
data_join_worker_cmd=/app/deploy/scripts/data_join/run_data_join_worker.sh


if [ -z "$CPU_LIMIT" ] && ([ -z "$PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER" ] || [ -z $SIGNER_OFFLOAD_PROCESSOR_NUMBER ])
then
  echo "Can't infer preprocessor_offload_processor_number for psi preprocessor and signer_offload_processor_number for psi signer"
  exit -1
fi

if [ "$PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER" ]
then
  echo "the user set preprocessor_offload_processor_number($PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER)"
elif [ "$SIGNER_OFFLOAD_PROCESSOR_NUMBER" ]
then
  export PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER=$(($CPU_LIMIT-$SIGNER_OFFLOAD_PROCESSOR_NUMBER-2))
  echo "we set preprocessor_offload_processor_number($PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER) by cpu_limit($CPU_LIMIT)-signer_offload_processor_number($SIGNER_OFFLOAD_PROCESSOR_NUMBER)-RESERVED_CPU(2)"
else
  echo "we set preprocessor_offload_processor_number($PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER) by (cpu_limit($CPU_LIMIT)-reserved_cpu(2))/2"
  export PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER=$((($CPU_LIMIT-2)/2))
fi

echo "launch the leader of psi preprocessor at background"
exec ${psi_preprocessor_cmd} &

if [ "$SIGNER_OFFLOAD_PROCESSOR_NUMBER" ]
then
  echo "the user set signer_offload_processor_number($SIGNER_OFFLOAD_PROCESSOR_NUMBER)"
else
  export SIGNER_OFFLOAD_PROCESSOR_NUMBER=$(($CPU_LIMIT-$PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER-2))
  echo "we set signer_offload_processor_number($SIGNER_OFFLOAD_PROCESSOR_NUMBER) by cpu_limit($CPU_LIMIT)-preprocessor_offload_processor_number($PREPROCESSOR_OFFLOAD_PROCESSOR_NUMBER)-RESERVED_CPU(2)"
fi
echo "launch psi signer for follower of psi preprocessor at front ground"
${psi_signer_cmd}
echo "psi signer for follower of psi preprocessor finish"

TCP_MSL=60
if [ -f "/proc/sys/net/ipv4/tcp_fin_timeout" ]
then
  TCP_MSL=`cat /proc/sys/net/ipv4/tcp_fin_timeout`
fi
SLEEP_TM=$((TCP_MSL * 3))
echo "sleep 3msl($SLEEP_TM) to make sure tcp state at CLOSED"
sleep $SLEEP_TM

echo "launch data join worker"
export RAW_DATA_ITER=$PSI_OUTPUT_BUILDER
export COMPRESSED_TYPE=$PSI_OUTPUT_BUILDER_COMPRESSED_TYPE
${data_join_worker_cmd}
echo "data join worker finish"

echo "waiting for background psi preprocessor exit"
wait
