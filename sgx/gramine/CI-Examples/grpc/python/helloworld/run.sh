set -x

unset http_proxy https_proxy

export HELLO_PATH=${GRPC_PATH}/examples/python/helloworld

# build python example
# ${HELLO_PATH}/build.sh

cp ${HELLO_PATH}/greeter_client.py ./grpc-client.py
cp ${HELLO_PATH}/greeter_server.py ./grpc-server.py

cp ${HELLO_PATH}/helloworld_pb2.py .
cp ${HELLO_PATH}/helloworld_pb2_grpc.py .

# build with graphene
make clean
make


function get_env() {
    graphene-sgx-get-token -sig=python.sig  | grep $1 | awk -F":" '{print $2}' | xargs
}

ls -l /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.so*
ls -l /usr/lib/x86_64-linux-gnu/libdcap_quoteprov.so*
ls -l /usr/lib/x86_64-linux-gnu/libsgx_default_qcnl_wrapper.so*

kill -9 `pgrep -f graphene`
graphene-sgx python -u ./grpc-server.py &
sleep 15s
graphene-sgx python -u ./grpc-client.py -mrs=`get_env mr_signer` -mre=`get_env mr_enclave`
