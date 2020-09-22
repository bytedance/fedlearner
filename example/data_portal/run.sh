#!/bin/bash

python make_data.py

INPUT_DIR=./data_portal_input_dir
OUTPUT_DIR=./data_portal_output_dir

python -m fedlearner.data_join.cmd.data_portal_master_service \
    --db_database=$DB_DATABASE \
    --db_addr=$DB_ADDR \
    --db_base_dir=$DB_BASE_DIR \
    --db_username=$DB_USERNAME \
    --db_password=$DB_PASSWORD \
    --listen_port=50051 \
    --data_portal_name=test_data_portal \
    --data_portal_type=Streaming \
    --output_partition_num=2 \
    --input_base_dir=${INPUT_DIR} \
    --output_base_dir=${OUTPUT_DIR} \
    --raw_data_publish_dir=raw_data_publish_dir \
    --use_mock_db > master.streaming.log 2>&1 &

master_pid=`echo $!`

python -m fedlearner.data_join.cmd.data_portal_worker_cli \
    --master_addr=localhost:50051 \
    --rank_id=0 \
    --db_database=$DB_DATABASE \
    --db_addr=$DB_ADDR \
    --db_base_dir=$DB_BASE_DIR \
    --db_username=$DB_USERNAME \
    --db_password=$DB_PASSWORD \
    --use_mock_db > worker.streaming.log 2>&1 &

worker_pid=`echo $!`
wait ${worker_pid} 
kill ${master_pid}
rm -rf $OUTPUT_DIR


python -m fedlearner.data_join.cmd.data_portal_master_service \
    --db_database=$DB_DATABASE \
    --db_addr=$DB_ADDR \
    --db_base_dir=$DB_BASE_DIR \
    --db_username=$DB_USERNAME \
    --db_password=$DB_PASSWORD \
    --listen_port=50051 \
    --data_portal_name=test_data_portal \
    --data_portal_type=PSI \
    --output_partition_num=2 \
    --input_base_dir=${INPUT_DIR} \
    --output_base_dir=${OUTPUT_DIR} \
    --raw_data_publish_dir=raw_data_publish_dir \
    --use_mock_db > master.PSI.log 2>&1 &

master_pid=`echo $!`

python -m fedlearner.data_join.cmd.data_portal_worker_cli \
    --master_addr=localhost:50051 \
    --rank_id=0 \
    --db_database=$DB_DATABASE \
    --db_addr=$DB_ADDR \
    --db_base_dir=$DB_BASE_DIR \
    --db_username=$DB_USERNAME \
    --db_password=$DB_PASSWORD \
    --use_mock_db > worker.PSI.log 2>&1 &

worker_pid=`echo $!`
wait ${worker_pid}
kill ${master_pid}
rm -rf $OUTPUT_DIR $INPUT_DIR



    