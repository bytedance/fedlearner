set -e
set -x

export MBEDTLS_PATH=${GRAPHENEDIR}/Examples/ra-tls-mbedtls
export HELLO_PATH=${GRPC_PATH}/examples/cpp/helloworld

# Build ra-tls-mbedtls
if [ ! -d "${MBEDTLS_PATH}/mbedtls" ]; then
    ${MBEDTLS_PATH}/build_install.sh
fi

# build c++ example
${HELLO_PATH}/build.sh

cp ${HELLO_PATH}/build/greeter_server ./grpc-server
cp ${HELLO_PATH}/build/greeter_client ./grpc-client
cp ${HELLO_PATH}/build/greeter_async_server ./grpc-async-server
cp ${HELLO_PATH}/build/greeter_async_client ./grpc-async-client
cp ${HELLO_PATH}/build/streaming_server ./streaming-server
cp ${HELLO_PATH}/build/streaming_client ./streaming-client

# build with graphene
make clean
make

ls -l /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.s*
