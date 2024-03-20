set -e

shopt -s expand_aliases
alias logfilter="grep \"mr_enclave\|mr_signer\|isv_prod_id\|isv_svn\""

# cp -r /home/host-home/0400h/fedlearner/sgx/grpc/v1.38.1/. ${GRPC_PATH}
# cp -r /home/host-home/0400h/fedlearner/sgx/gramine/CI-Examples/. ${GRAMINEDIR}/CI-Examples

export EXP_PATH=${GRPC_PATH}/examples
export EXP_PY_PATH=${EXP_PATH}/python/helloworld

function get_env() {
    gramine-sgx-get-token -s python.sig -o /dev/null | grep $1 | awk -F ":" '{print $2}' | xargs
}

# build example
${EXP_PY_PATH}/build.sh

# copy examples
cp ${EXP_PY_PATH}/greeter_client.py ./grpc-client.py
cp ${EXP_PY_PATH}/greeter_server.py ./grpc-server.py
cp ${EXP_PY_PATH}/helloworld_pb2.py .
cp ${EXP_PY_PATH}/helloworld_pb2_grpc.py .

# build and generate config json with gramine
make clean && make | logfilter
jq ' .sgx_mrs[0].mr_enclave = ''"'`get_env mr_enclave`'" | .sgx_mrs[0].mr_signer = ''"'`get_env mr_signer`'" ' ${EXP_PATH}/dynamic_config.json > ./dynamic_config.json

kill -9 `pgrep -f gramine`
