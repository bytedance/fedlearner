#!/bin/bash
set -e

if  [ ! -n "$1" ] ; then
    tag=latest
else
    tag=$1
fi

cd ..
# You can remove build-arg http_proxy and https_proxy if your network doesn't need it
#no_proxy="localhost,127.0.0.0/1"
proxy_server="http://child-prc.intel.com:913"

DOCKER_BUILDKIT=0 docker build \
    -f fedlearner-sgx-dev.dockerfile . \
    -t fedlearner-sgx-dev:${tag} \
    --network=host \
    --build-arg http_proxy=${proxy_server} \
    --build-arg https_proxy=${proxy_server} \
    --build-arg no_proxy=${no_proxy}
