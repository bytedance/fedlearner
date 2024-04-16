set -ex

export BUILD_TYPE=Release
export HELLO_PATH=${GRPC_PATH}/examples/cpp/helloworld

${GRPC_PATH}/build_cpp.sh

# build c++ example
cd ${HELLO_PATH}
mkdir -p build
cd build
cmake -D CMAKE_PREFIX_PATH=${INSTALL_PREFIX} -D CMAKE_BUILD_TYPE=${BUILD_TYPE} ..
make -j `nproc`
cd -
