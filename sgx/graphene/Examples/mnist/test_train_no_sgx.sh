#!/bin/bash
set -e
set -x

shopt -s expand_aliases
alias logfilter="grep -v \"FUTEX\|measured\|memory entry\|cleaning up\|async event\|shim_exit\""

export CUDA_VISIBLE_DEVICES=""

function get_env() {
    graphene-sgx-get-token -sig=python.sig  | grep $1 | awk -F":" '{print $2}' | xargs
}

function make_custom_env() {
    export TF_GRPC_TLS_ENABLE=on
    export MR_ENCLAVE=`get_env mr_enclave`
    export MR_SIGNER=`get_env mr_signer`
    export ISV_PROD_ID=`get_env isv_prod_id`
    export ISV_SVN=`get_env isv_svn`
    # make no sense right now
    export parallel_num_threads=2
    export session_parallelism=0
    export intra_op_parallelism=2
    export inter_op_parallelism=2
    export OMP_NUM_THREADS=2
    export MKL_NUM_THREADS=2
}

#make_custom_env

alias logfilter="grep -v \"FUTEX\|measured\|memory entry\|cleaning up\|async event\|shim_exit\""

>ps0-graphene-python.log
>worker0-graphene-python.log
python -u train.py --task_index=0 --job_name=ps --loglevel=debug 2>&1 | logfilter | tee -a ps0-graphene-python.log & 
python -u train.py --task_index=0 --job_name=worker --loglevel=debug 2>&1 | logfilter | tee -a worker0-graphene-python.log &
