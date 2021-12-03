#!/bin/bash
set -ex

shopt -s expand_aliases
alias make_logfilter="grep \"mr_enclave\|mr_signer\|isv_prod_id\|isv_svn\""
alias runtime_logfilter="grep -v \"FUTEX\|measured\|memory entry\|cleaning up\|async event\|shim_exit\""

function get_env() {
    gramine-sgx-get-token -s python.sig -o /dev/null | grep $1 | awk -F ":" '{print $2}' | xargs
}

function make_custom_env() {
    export DEBUG=0
    export CUDA_VISIBLE_DEVICES=""
    export DNNL_VERBOSE=1
    export GRPC_VERBOSITY=ERROR
    export TF_CPP_MIN_LOG_LEVEL=1
    export TF_GRPC_SGX_RA_TLS_ENABLE=on
    export TF_DISABLE_MKL=0
    export TF_ENABLE_MKL_NATIVE_FORMAT=1
    export parallel_num_threads=4
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    export KMP_SETTINGS=1
    export KMP_BLOCKTIME=0
    export MR_ENCLAVE=`get_env mr_enclave`
    export MR_SIGNER=`get_env mr_signer`
    export ISV_PROD_ID=`get_env isv_prod_id`
    export ISV_SVN=`get_env isv_svn`
    # network proxy
    unset http_proxy https_proxy
}

ROLE=$1
if [ "$ROLE" == "make" ]; then
    rm -rf model *.log
    make clean && make | make_logfilter
    kill -9 `pgrep -f gramine`
elif [ "$ROLE" == "ps" ]; then
    make_custom_env
    taskset -c 0-3 stdbuf -o0 gramine-sgx python -u train.py --task_index=0 --job_name=ps --loglevel=debug 2>&1 | runtime_logfilter | tee -a ps0-gramine-python.log &
    if [ "$DEBUG" != "0" ]; then
        wait && kill -9 `pgrep -f gramine`
    fi
elif [ "$ROLE" == "worker" ]; then
    make_custom_env
    taskset -c 4-7 stdbuf -o0 gramine-sgx python -u train.py --task_index=0 --job_name=worker --loglevel=debug 2>&1 | runtime_logfilter | tee -a worker0-gramine-python.log &
    if [ "$DEBUG" != "0" ]; then
        wait && kill -9 `pgrep -f gramine`
    fi
fi
