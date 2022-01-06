#!/bin/bash
set -ex

source /app/deploy/scripts/hdfs_common.sh
source /app/deploy/scripts/env_to_args.sh

if [[ -n "${CODE_KEY}" ]]; then
  pull_code ${CODE_KEY} $PWD
fi

if [[ $ROLE == "leader" ]]; then
  export FL_LEADER_ADDRESS="0.0.0.0:50051"
elif [[ -n $PEER_ADDR ]]; then
  export FL_LEADER_ADDRESS=$PEER_ADDR
fi

python $ROLE.py 