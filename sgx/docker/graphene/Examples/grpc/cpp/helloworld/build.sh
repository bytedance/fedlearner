set -e

# cp -r /home/host-home/0400h/cloud-tee/fedlearner/docker/grpc/* ${GRPC_PATH}
# cp -r /home/host-home/0400h/cloud-tee/fedlearner/docker/graphene/* ${GRAPHENEDIR}

export HELLO_PATH=${GRPC_PATH}/examples/cpp/helloworld

# build c++ example
${HELLO_PATH}/build.sh

cp ${HELLO_PATH}/build/greeter_server ./grpc-server
cp ${HELLO_PATH}/build/greeter_client ./grpc-client

# build with graphene
make clean
make

ls -l /usr/lib/x86_64-linux-gnu/libsgx_dcap_quoteverify.s*
