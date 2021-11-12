set -ex

# build grpc c / cpp library
${GRPC_PATH}/build_cpp.sh

# build grpc python wheel
cd ${GRPC_PATH}
rm -rf python_build None src/python/grpcio/__pycache__ src/python/grpcio/grpc/_cython/cygrpc.cpp
python3 setup.py bdist_wheel
cd -

ldd ${GRPC_PATH}/python_build/lib.linux-x86_64-3.6/grpc/_cython/cygrpc.cpython-36m-x86_64-linux-gnu.so
