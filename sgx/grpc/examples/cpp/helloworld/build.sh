set -e

export BUILD_TYPE=Debug

export MBEDTLS_PATH=${GRAPHENEDIR}/Examples/ra-tls-mbedtls
export HELLO_PATH=${GRPC_PATH}/examples/cpp/helloworld

# Build ra-tls-mbedtls
if [ ! -d "${MBEDTLS_PATH}/mbedtls" ]; then
    ${MBEDTLS_PATH}/build_install.sh
fi

# build c++ example
cd ${HELLO_PATH}
mkdir -p build
cd build
cmake -D CMAKE_PREFIX_PATH=${INSTALL_PREFIX} -D CMAKE_BUILD_TYPE=${BUILD_TYPE} ..
make -j `nproc`
cd -
