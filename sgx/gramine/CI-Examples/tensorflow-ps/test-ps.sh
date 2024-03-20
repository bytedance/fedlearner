#!/bin/bash
set -x

function make_custom_env() {
    export CUDA_VISIBLE_DEVICES=""
    export DNNL_VERBOSE=0
    export GRPC_VERBOSITY=ERROR
    export GRPC_POLL_STRATEGY=epoll1
    export TF_CPP_MIN_LOG_LEVEL=1
    export TF_GRPC_SGX_RA_TLS_ENABLE=""
    export TF_DISABLE_MKL=0
    export TF_ENABLE_MKL_NATIVE_FORMAT=1
    export parallel_num_threads=4
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    export KMP_SETTINGS=1
    export KMP_BLOCKTIME=0
    # network proxy
    unset http_proxy https_proxy
}

ROLE=$1
if [ "$ROLE" == "ps0" ]; then
    kill -9 `pgrep -f python`
    make_custom_env
    taskset -c 0-3 stdbuf -o0 python -u train.py --task_index=0 --job_name=ps --loglevel=debug 2>&1 | tee -a ps0-native.log &
elif [ "$ROLE" == "ps1" ]; then
    make_custom_env
    taskset -c 8-11 stdbuf -o0 python -u train.py --task_index=1 --job_name=ps --loglevel=debug 2>&1 | tee -a ps1-native.log &
elif [ "$ROLE" == "worker0" ]; then
    make_custom_env
    taskset -c 4-7 stdbuf -o0 python -u train.py --task_index=0 --job_name=worker --loglevel=debug 2>&1 | tee -a worker0-native.log &
elif [ "$ROLE" == "worker1" ]; then
    make_custom_env
    taskset -c 12-15 stdbuf -o0 python -u train.py --task_index=1 --job_name=worker --loglevel=debug 2>&1 | tee -a worker1-native.log &
fi
