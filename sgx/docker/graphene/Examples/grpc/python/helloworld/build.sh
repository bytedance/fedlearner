set -e

cp -r /home/host-home/0400h/cloud-tee/fedlearner/docker/grpc/* ${GRPC_PATH}
cp -r /home/host-home/0400h/cloud-tee/fedlearner/docker/graphene/* ${GRAPHENEDIR}

export HELLO_PATH=${GRPC_PATH}/examples/python/helloworld

# build python example
${HELLO_PATH}/build.sh

cp ${HELLO_PATH}/greeter_client.py ./grpc-client.py
cp ${HELLO_PATH}/greeter_server.py ./grpc-server.py

cp ${HELLO_PATH}/helloworld_pb2.py .
cp ${HELLO_PATH}/helloworld_pb2_grpc.py .

# build with graphene
make clean
make

ls -l /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.s*
