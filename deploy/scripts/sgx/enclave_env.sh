#!/bin/bash

# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

EXEC_DIR=/app/exec_dir

function get_env() {
    gramine-sgx-get-token -s python.sig -o /dev/null | grep $1 | awk -F ":" '{print $2}' | xargs
}

function make_custom_env() {
    cd $EXEC_DIR

    export DEBUG=0
    export CUDA_VISIBLE_DEVICES=""
    export DNNL_VERBOSE=0
    export GRPC_VERBOSITY=ERROR
    export GRPC_POLL_STRATEGY=epoll1
    export TF_CPP_MIN_LOG_LEVEL=1
    export TF_GRPC_SGX_RA_TLS_ENABLE=on
    export FL_GRPC_SGX_RA_TLS_ENABLE=on
    export TF_DISABLE_MKL=0
    export TF_ENABLE_MKL_NATIVE_FORMAT=1
    export parallel_num_threads=$1
    export INTRA_OP_PARALLELISM_THREADS=$parallel_num_threads
    export INTER_OP_PARALLELISM_THREADS=$parallel_num_threads
    export GRPC_SERVER_CHANNEL_THREADS=4
    export KMP_SETTINGS=1
    export KMP_BLOCKTIME=0
    export HADOOP_HOME=${HADOOP_HOME:-/opt/tiger/yarn_deploy/hadoop_current}
    export PATH=$PATH:${HADOOP_HOME}/bin
    export JAVA_HOME=/opt/tiger/jdk/openjdk-1.8.0_265
    export LD_LIBRARY_PATH=${HADOOP_HOME}/lib/native:${JAVA_HOME}/jre/lib/amd64/server:${LD_LIBRARY_PATH}
    export CLASSPATH=.:$CLASSPATH:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar:$($HADOOP_HOME/bin/hadoop classpath --glob)
    export MR_ENCLAVE=`get_env mr_enclave`
    export MR_SIGNER=`get_env mr_signer`
    export ISV_PROD_ID=`get_env isv_prod_id`
    export ISV_SVN=`get_env isv_svn`
    export RA_TLS_ALLOW_OUTDATED_TCB_INSECURE=1

    if [ -z "$PEER_MR_SIGNER" ]; then
        export PEER_MR_SIGNER=`get_env mr_signer`
    fi

    if [ -z "$PEER_MR_ENCLAVE" ]; then
        export PEER_MR_ENCLAVE=`get_env mr_enclave`
    fi

    # network proxy
    unset http_proxy https_proxy
    # need meituan's
    jq --arg mr_enclave "$PEER_MR_ENCLAVE" --arg mr_signer "$PEER_MR_SIGNER" \
        '.sgx_mrs[0].mr_enclave = $mr_enclave | .sgx_mrs[0].mr_signer = $mr_signer' \
        $GRPC_PATH/examples/dynamic_config.json > $EXEC_DIR/dynamic_config.json
    
    cd -
}

function generate_token() {
    cd /gramine/CI-Examples/generate-token/
    ./generate.sh
    mkdir -p $EXEC_DIR
    cp /app/sgx/gramine/CI-Examples/tensorflow_io.py $EXEC_DIR
    cp python.sig $EXEC_DIR
    cp python.manifest.sgx $EXEC_DIR
    cp python.token $EXEC_DIR
    cp python.manifest $EXEC_DIR
    cd -
}

if [ -n "$PCCS_IP" ]; then
        sed -i "s|PCCS_URL=https://[^ ]*|PCCS_URL=https://pccs_url:8081/sgx/certification/v3/|" /etc/sgx_default_qcnl.conf
        echo >> /etc/hosts
        echo "$PCCS_IP   pccs_url" | tee -a /etc/hosts
elif [ -n "$PCCS_URL" ]; then
        sed -i "s|PCCS_URL=[^ ]*|PCCS_URL=$PCCS_URL|" /etc/sgx_default_qcnl.conf
fi

TEMPLATE_PATH="/gramine/CI-Examples/generate-token/python.manifest.template"
if [ -n "$GRAMINE_LOG_LEVEL" ]; then
        sed -i "/loader.log_level/ s/\"[^\"]*\"/\"$GRAMINE_LOG_LEVEL\"/" "$TEMPLATE_PATH"
        if [ $? -eq 0 ]; then
            echo "Log level changed to $GRAMINE_LOG_LEVEL in $TEMPLATE_PATH"
        else
            echo "Failed to change log level in $TEMPLATE_PATH"
        fi
fi

if [ -n "$GRAMINE_ENCLAVE_SIZE" ]; then
    sed -i "/sgx.enclave_size/ s/\"[^\"]*\"/\"$GRAMINE_ENCLAVE_SIZE\"/" "$TEMPLATE_PATH"
    if [ $? -eq 0 ]; then
        echo "Enclave size changed to $GRAMINE_ENCLAVE_SIZE in $TEMPLATE_PATH"
    else
        echo "Failed to change enclave size in $TEMPLATE_PATH"
    fi
fi

if [ -n "$GRAMINE_THREAD_NUM" ]; then
    sed -i "s/sgx.thread_num = [0-9]\+/sgx.thread_num = $GRAMINE_THREAD_NUM/" "$TEMPLATE_PATH"
    if [ $? -eq 0 ]; then
        echo "Thread number changed to $GRAMINE_THREAD_NUM in $TEMPLATE_PATH"
    else
        echo "Failed to change thread number in $TEMPLATE_PATH"
    fi
fi

if [ -n "$GRAMINE_STACK_SIZE" ]; then
    sed -i "/sys.stack.size/ s/\"[^\"]*\"/\"$GRAMINE_STACK_SIZE\"/" "$TEMPLATE_PATH"
    if [ $? -eq 0 ]; then
        echo "Stack size changed to $GRAMINE_STACK_SIZE in $TEMPLATE_PATH"
    else
        echo "Failed to change stack size in $TEMPLATE_PATH"
    fi
fi

sed -i 's/USE_SECURE_CERT=TRUE/USE_SECURE_CERT=FALSE/' /etc/sgx_default_qcnl.conf
mkdir -p /data

generate_token