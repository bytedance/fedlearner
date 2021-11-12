#!/bin/bash
set -ex

function make_custom_env() {
    export CUDA_VISIBLE_DEVICES=""
    export GRPC_VERBOSITY=ERROR
    export TF_GRPC_SGX_RA_TLS_ENABLE=""
    export TF_CPP_MIN_LOG_LEVEL=1
    export parallel_num_threads=4
    export session_parallelism=0
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    # network proxy
    unset http_proxy https_proxy
}

ROLE=$1
if [ "$ROLE" == "ps" ]; then
    make_custom_env
    taskset -c 0-3 stdbuf -o0 python -u train.py --task_index=0 --job_name=ps --loglevel=debug 2>&1 | tee -a ps0-python.log &
elif [ "$ROLE" == "worker" ]; then
    make_custom_env
    taskset -c 0-3 stdbuf -o0 python -u train.py --task_index=0 --job_name=worker --loglevel=debug 2>&1 | tee -a worker0-python.log &
fi
