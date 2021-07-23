#!/bin/bash
set -e

if  [ ! -n "$1" ] ; then
    tag=latest
else
    tag=$1
fi

docker run -it \
    --restart=always \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    --device=/dev/sgx_enclave:/dev/sgx/enclave \
    --device=/dev/sgx_provision:/dev/sgx/provision \
    -v /opt/intel/sgxsdk:/opt/intel/sgxsdk \
    -v /home:/home/host-home \
    --add-host=pa.com:127.0.0.1 \
    --add-host=pb.com:127.0.0.1 \
    --add-host=attestation.service.com:10.239.173.66 \
    fedlearner-sgx-dev:${tag} \
    bash
