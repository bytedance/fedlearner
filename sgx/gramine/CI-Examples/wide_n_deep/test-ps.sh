#!/bin/bash
set -x

function make_custom_env() {
    export CUDA_VISIBLE_DEVICES=""
    export DNNL_VERBOSE=1
    export GRPC_VERBOSITY=ERROR
    export GRPC_POLL_STRATEGY=epoll1
    export TF_CPP_MIN_LOG_LEVEL=1
    export TF_GRPC_SGX_RA_TLS_ENABLE=""
    export FL_GRPC_SGX_RA_TLS_ENABLE=""
    export TF_DISABLE_MKL=0
    export TF_ENABLE_MKL_NATIVE_FORMAT=1
    export parallel_num_threads=4
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    export GRPC_SERVER_CHANNEL_THREADS=16
    export KMP_SETTINGS=1
    export KMP_BLOCKTIME=0
    # network proxy
    unset http_proxy https_proxy
}

ROLE=$1
if [ "$ROLE" == "data" ]; then
    rm -rf data model *.log
    cp ../tensorflow_io.py .
    cp -r ${FEDLEARNER_PATH}/example/wide_n_deep/*.py .
    python make_data.py
elif [ "$ROLE" == "leader" ]; then
    kill -9 `pgrep -f python`
    make_custom_env
    rm -rf model/leader
    taskset -c 0-3 python -u -m fedlearner.trainer.parameter_server localhost:40051 2>&1 | tee -a leader-ps.log & 
    taskset -c 4-7 python -u leader.py --local-addr=localhost:50051                                    \
                                       --peer-addr=localhost:50052                                     \
                                       --data-path=data/leader                                         \
                                       --checkpoint-path=model/leader/checkpoint                       \
                                       --export-path=model/leader/saved_model                          \
                                       --save-checkpoint-steps=10                                      \
                                       --epoch-num=2                                                   \
                                       --batch-size=32                                                 \
                                       --cluster-spec='{"clusterSpec":{"PS":["localhost:40051"]}}'     \
                                       --loglevel=debug 2>&1 | tee -a leader-native.log &
elif [ "$ROLE" == "follower" ]; then
    make_custom_env
    rm -rf model/follower
    taskset -c 8-11  python -u -m fedlearner.trainer.parameter_server localhost:40061 2>&1 | tee -a follower-ps.log & 
    taskset -c 12-15 python -u follower.py --local-addr=localhost:50052                                   \
                                           --peer-addr=localhost:50051                                    \
                                           --data-path=data/follower                                      \
                                           --checkpoint-path=model/follower/checkpoint                    \
                                           --export-path=model/follower/saved_model                       \
                                           --save-checkpoint-steps=10                                     \
                                           --epoch-num=2                                                  \
                                           --batch-size=32                                                \
                                           --cluster-spec='{"clusterSpec":{"PS":["localhost:40061"]}}'    \
                                           --loglevel=debug 2>&1 | tee -a follower-native.log &
fi
