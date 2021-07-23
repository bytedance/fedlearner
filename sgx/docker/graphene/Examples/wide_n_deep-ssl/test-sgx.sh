#!/bin/bash
set -e

shopt -s expand_aliases
alias logfilter="grep -v \"FUTEX\|measured\|memory entry\|cleaning up\|async event\|shim_exit\""

export CUDA_VISIBLE_DEVICES=""

ROLE=$1
if [ "${ROLE}" == "data" ]; then
    rm -rf data
    python make_data.py
fi

unset http_proxy https_proxy

export DEBUG=0
export parallel_num_threads=16
export session_parallelism=0
export intra_op_parallelism=${parallel_num_threads}
export inter_op_parallelism=${parallel_num_threads}
export OMP_NUM_THREADS=${parallel_num_threads}
export MKL_NUM_THREADS=${parallel_num_threads}

if [ "${ROLE}" == "leader" ]; then
    export CERT_BASE_DIR=xxx/pa
    rm -rf model/leader leader-graphene-python.log
    make clean && make ROLE=1
    taskset -c 0-15 graphene-sgx python -u leader.py --local-addr=pa.com:50051                                   \
                                                     --peer-addr=pb.com:50052                                    \
                                                     --data-path=data/leader                                     \
                                                     --checkpoint-path=model/leader/checkpoint                   \
                                                     --export-path=model/leader/saved_model                      \
                                                     --save-checkpoint-steps=10                                  \
                                                     --epoch_num=2                                               \
                                                     2>&1 | logfilter | tee -a leader-graphene-python.log &
    if [ "${DEBUG}" != "0" ]; then
        wait && kill -9 `pgrep -f graphene`
    fi
elif [ "${ROLE}" == "follower" ]; then
    export CERT_BASE_DIR=xxx/pb
    rm -rf model/follower follower-graphene-python.log
    make clean && make ROLE=0
    taskset -c 16-31 graphene-sgx python -u follower.py --local-addr=pb.com:50052                                \
                                                        --peer-addr=pa.com:50051                                 \
                                                        --data-path=data/follower                                \
                                                        --checkpoint-path=model/follower/checkpoint              \
                                                        --export-path=model/follower/saved_model                 \
                                                        --save-checkpoint-steps=10                               \
                                                        --epoch_num=2                                            \
                                                        2>&1 | logfilter | tee -a follower-graphene-python.log &
    if [ "${DEBUG}" != "0" ]; then
        wait && kill -9 `pgrep -f graphene`
    fi
fi
