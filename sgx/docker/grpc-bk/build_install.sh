set -e

# build and install grpc library
cd ${GRPC_PATH}
mkdir -p build
cd build
cmake -DgRPC_INSTALL=ON -DgRPC_BUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX} ..
make -j `nproc`
make install
cd -

# build and install abseil
if [ ! -d "${INSTALL_PREFIX}/include/absl" ]; then
    cd ${GRPC_PATH}/third_party/abseil-cpp
    mkdir -p build
    cd build
    cmake -DCMAKE_POSITION_INDEPENDENT_CODE=TRUE -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX} ..
    make -j `nproc`
    make install
    cd -
fi
