#!/bin/bash
set -e
set -x

shopt -s expand_aliases
alias logfilter="grep -v \"FUTEX\|measured\|memory entry\|cleaning up\|async event\|shim_exit\""

export CUDA_VISIBLE_DEVICES=""

custom_env="custom_env"
function get_env() {
    graphene-sgx-get-token -sig=python.sig  | grep $1 | awk -F":" '{print $2}' | xargs
}

function make_custom_env() {
    echo "TF_OPTIONAL_TLS_ENABLE=on" > $custom_env 
    echo "MR_ENCLAVE=`get_env mr_enclave`" >> $custom_env
    echo "MR_SIGNER=`get_env mr_signer`" >> $custom_env
    echo "ISV_PROD_ID=`get_env isv_prod_id`" >> $custom_env
    echo "ISV_SVN=`get_env isv_svn`" >> $custom_env

    echo "DEBUG=0" >> $custom_env
    echo "parallel_num_threads=2" >> $custom_env
    echo "session_parallelism=0" >> $custom_env
    echo "intra_op_parallelism=${parallel_num_threads}" >> $custom_env
    echo "inter_op_parallelism=${parallel_num_threads}" >> $custom_env
    echo "OMP_NUM_THREADS=${parallel_num_threads}" >> $custom_env
    echo "MKL_NUM_THREADS=${parallel_num_threads}" >> $custom_env
}

make_custom_env

alias logfilter="grep -v \"FUTEX\|measured\|memory entry\|cleaning up\|async event\|shim_exit\""

>ps0-graphene-python.log
>worker0-graphene-python.log
graphene-sgx python -u train.py --task_index=0 --job_name=ps --loglevel=debug 2>&1 | logfilter | tee -a ps0-graphene-python.log & 
graphene-sgx python -u train.py --task_index=0 --job_name=worker --loglevel=debug 2>&1 | logfilter | tee -a worker0-graphene-python.log &

