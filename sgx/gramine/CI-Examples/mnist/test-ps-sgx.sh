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
    export GRPC_POLL_STRATEGY=epoll1
    export TF_CPP_MIN_LOG_LEVEL=1
    export TF_GRPC_SGX_RA_TLS_ENABLE=on
    export FL_GRPC_SGX_RA_TLS_ENABLE=on
    export TF_DISABLE_MKL=0
    export TF_ENABLE_MKL_NATIVE_FORMAT=1
    export parallel_num_threads=4
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    export GRPC_SERVER_CHANNEL_THREADS=2
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
if [ "$ROLE" == "data" ]; then
    rm -rf data
    cp ../tensorflow_io.py .
    cp -r $FEDLEARNER_PATH/example/mnist/*.py .
    python make_data.py
elif [ "$ROLE" == "make" ]; then
    rm -rf *.log model
    make clean && make | make_logfilter
    jq ' .sgx_mrs[0].mr_enclave = ''"'`get_env mr_enclave`'" | .sgx_mrs[0].mr_signer = ''"'`get_env mr_signer`'" ' $GRPC_PATH/examples/dynamic_config.json > ./dynamic_config.json
    kill -9 `pgrep -f gramine`
elif [ "$ROLE" == "leader" ]; then
    make_custom_env
    rm -rf model/leader
    taskset -c 0-3 stdbuf -o0 gramine-sgx python -u -m fedlearner.trainer.parameter_server localhost:40051 2>&1 | runtime_logfilter | tee -a leader-gramine-ps.log & 
    taskset -c 4-7 stdbuf -o0 gramine-sgx python -u leader.py --local-addr=localhost:50051                                    \
                                                              --peer-addr=localhost:50052                                     \
                                                              --data-path=data/leader                                         \
                                                              --checkpoint-path=model/leader/checkpoint                       \
                                                              --export-path=model/leader/saved_model                          \
                                                              --save-checkpoint-steps=10                                      \
                                                              --epoch-num=2                                                   \
                                                              --batch-size=32                                                 \
                                                              --cluster-spec='{"clusterSpec":{"PS":["localhost:40051"]}}'     \
                                                              --loglevel=debug 2>&1 | runtime_logfilter | tee -a leader-gramine.log &
    if [ "$DEBUG" != "0" ]; then
        wait && kill -9 `pgrep -f gramine`
    fi
elif [ "$ROLE" == "follower" ]; then
    make_custom_env
    rm -rf model/follower
    taskset -c 8-11 stdbuf -o0 gramine-sgx python -u -m fedlearner.trainer.parameter_server localhost:40061 2>&1 | runtime_logfilter | tee -a follower-gramine-ps.log & 
    taskset -c 12-15 stdbuf -o0 gramine-sgx python -u follower.py --local-addr=localhost:50052                                   \
                                                                  --peer-addr=localhost:50051                                    \
                                                                  --data-path=data/follower                                      \
                                                                  --checkpoint-path=model/follower/checkpoint                    \
                                                                  --export-path=model/follower/saved_model                       \
                                                                  --save-checkpoint-steps=10                                     \
                                                                  --epoch-num=2                                                  \
                                                                  --batch-size=32                                                \
                                                                  --cluster-spec='{"clusterSpec":{"PS":["localhost:40061"]}}'    \
                                                                  --loglevel=debug 2>&1 | runtime_logfilter | tee -a follower-gramine.log &
    if [ "$DEBUG" != "0" ]; then
        wait && kill -9 `pgrep -f gramine`
    fi
fi
