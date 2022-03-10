#!/bin/bash
set -e

if  [ ! -n "$1" ] ; then
    image_tag=latest
else
    image_tag=$1
fi

cd `dirname "$0"`/..

# You can remove build-arg http_proxy and https_proxy if your network doesn't need it
no_proxy="localhost,127.0.0.1"
proxy_server="http://test-proxy:port"

DOCKER_BUILDKIT=0 docker build \
    -f fedlearner-sgx-dev.dockerfile \
    -t fedlearner-sgx-dev:${image_tag} \
    --network=host \
    --build-arg http_proxy=${proxy_server} \
    --build-arg https_proxy=${proxy_server} \
    --build-arg no_proxy=${no_proxy} \
    .

cd -
