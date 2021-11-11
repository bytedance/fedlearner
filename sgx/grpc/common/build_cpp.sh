set -ex

export ABSEIL_PATH=${GRPC_PATH}/third_party/abseil-cpp

if [ ! -d "${BUILD_TYPE}" ]; then
    BUILD_TYPE=Release
fi

# build and install abseil library
# https://abseil.io/docs/cpp/quickstart-cmake.html
if [ ! -d "${ABSEIL_PATH}/build" ]; then
    mkdir -p ${ABSEIL_PATH}/build
    cd ${ABSEIL_PATH}/build
    cmake -DCMAKE_CXX_STANDARD=11 -DCMAKE_POSITION_INDEPENDENT_CODE=TRUE \
          -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX} ..
    make -j `nproc`
    make install
    cd -
fi

# build and install grpc library
mkdir -p ${GRPC_PATH}/build
cd ${GRPC_PATH}/build
cmake -DgRPC_INSTALL=ON -DABSL_ENABLE_INSTALL=ON \
      -DgRPC_ABSL_PROVIDER=package -DgRPC_BUILD_TESTS=OFF \
      -DgRPC_BUILD_CSHARP_EXT=OFF -DgRPC_BUILD_GRPC_CSHARP_PLUGIN=OFF \
      -DgRPC_BUILD_GRPC_PHP_PLUGIN=OFF -DgRPC_BUILD_GRPC_RUBY_PLUGIN=OFF \
      -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX} ..
make -j `nproc`
make install
cd -
