#!/bin/bash

set -ex

export CUDA_VISIBLE_DEVICES=

python -m fedlearner.data_join.data_join_master \
    $REMOTE_IP \
    --etcd_name=$ETCD_NAME \
    --etcd_addrs=$ETCD_ADDR \
    --etcd_base_dir=$ETCD_BASE_DIR \
    --listen_port=$PORT0 \
    --data_source_name=$DATA_SOURCE_NAME
