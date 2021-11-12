set -e

shopt -s expand_aliases
alias logfilter="grep \"mr_enclave\|mr_signer\|isv_prod_id\|isv_svn\""

# cp -r /home/host-home/0400h/fedlearner/sgx/grpc/v1.38.1/. ${GRPC_PATH}
# cp -r /home/host-home/0400h/fedlearner/sgx/gramine/CI-Examples/. ${GRAMINEDIR}/CI-Examples

export EXP_PATH=${GRPC_PATH}/examples
export EXP_CPP_PATH=${EXP_PATH}/cpp
export RUNTIME_PATH=`pwd -P`/../tmp

function get_env() {
    gramine-sgx-get-token -s grpc.sig -o /dev/null | grep $1 | awk -F ":" '{print $2}' | xargs
}


function prepare_runtime() {
    make clean && GRAPHENE_ENTRYPOINT=$1 make | logfilter && cp -r `pwd -P` ${RUNTIME_PATH}/$1
}

function generate_json() {
    cd ${RUNTIME_PATH}/$1
    jq ' .sgx_mrs[0].mr_enclave = ''"'`get_env mr_enclave`'" | .sgx_mrs[0].mr_signer = ''"'`get_env mr_signer`'" ' ${EXP_PATH}/dynamic_config.json > ${RUNTIME_PATH}/$2/dynamic_config.json
    cd -
}

# build examples
${EXP_CPP_PATH}/helloworld/build.sh
${EXP_CPP_PATH}/keyvaluestore/build.sh

# copy examples
cp ${EXP_CPP_PATH}/helloworld/build/greeter_server .
cp ${EXP_CPP_PATH}/helloworld/build/greeter_client .
cp ${EXP_CPP_PATH}/helloworld/build/greeter_async_server .
cp ${EXP_CPP_PATH}/helloworld/build/greeter_async_client .
cp ${EXP_CPP_PATH}/keyvaluestore/build/server ./stream_server
cp ${EXP_CPP_PATH}/keyvaluestore/build/client ./stream_client

# create runtime dir
mkdir -p ${RUNTIME_PATH}
rm -rf ${RUNTIME_PATH}/*

# prepare runtime with gramine
prepare_runtime greeter_server
prepare_runtime greeter_client
prepare_runtime greeter_async_server
prepare_runtime greeter_async_client
prepare_runtime stream_server
prepare_runtime stream_client

# generate config json for sgx
generate_json greeter_server greeter_client
generate_json greeter_client greeter_server
generate_json greeter_async_server greeter_async_client
generate_json greeter_async_client greeter_async_server
generate_json stream_server stream_client
generate_json stream_client stream_server

kill -9 `pgrep -f gramine`
