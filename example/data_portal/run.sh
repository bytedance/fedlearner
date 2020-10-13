#!/bin/bash

python make_data.py

INPUT_DIR=./data_portal_input_dir
OUTPUT_DIR=./data_portal_output_dir
KVSTORE_TYPE='mock'

python -m fedlearner.data_join.cmd.data_portal_master_service \
    --kvstore_type=$KVSTORE_TYPE
    --listen_port=50051 \
    --data_portal_name=test_data_portal \
    --data_portal_type=Streaming \
    --output_partition_num=2 \
    --input_base_dir=${INPUT_DIR} \
    --output_base_dir=${OUTPUT_DIR} \
    --raw_data_publish_dir=raw_data_publish_dir \
    > master.streaming.log 2>&1 &

master_pid=`echo $!`

python -m fedlearner.data_join.cmd.data_portal_worker_cli \
    --master_addr=localhost:50051 \
    --rank_id=0 \
    --kvstore_type=$KVSTORE_TYPE \
    > worker.streaming.log 2>&1 &

worker_pid=`echo $!`
wait ${worker_pid} 
kill ${master_pid}
rm -rf $OUTPUT_DIR


python -m fedlearner.data_join.cmd.data_portal_master_service \
    --kvstore_type=$KVSTORE_TYPE
    --listen_port=50051 \
    --data_portal_name=test_data_portal \
    --data_portal_type=PSI \
    --output_partition_num=2 \
    --input_base_dir=${INPUT_DIR} \
    --output_base_dir=${OUTPUT_DIR} \
    --raw_data_publish_dir=raw_data_publish_dir \
    > master.PSI.log 2>&1 &

master_pid=`echo $!`

python -m fedlearner.data_join.cmd.data_portal_worker_cli \
    --master_addr=localhost:50051 \
    --rank_id=0 \
    --kvstore_type=$KVSTORE_TYPE
    > worker.PSI.log 2>&1 &

worker_pid=`echo $!`
wait ${worker_pid}
kill ${master_pid}
rm -rf $OUTPUT_DIR $INPUT_DIR



    