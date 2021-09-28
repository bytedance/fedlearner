set -e

# build grpc c / cpp library
${GRPC_PATH}/build_cpp.sh

# build grpc python wheel
cd ${GRPC_PATH}
rm -rf python_build None src/python/grpcio/__pycache__ src/python/grpcio/grpc/_cython/cygrpc.cpp
python3 setup.py bdist_wheel
cd -

ldd ${GRPC_PATH}/src/python/grpcio/grpc/_cython/cygrpc.cpython-*.so
