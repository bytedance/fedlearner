#!/bin/bash

function get_token(){
    local need_clean=0
    cd /gramine/CI-Examples/generate-token/
    make clean > /dev/null
    export SGX=1
    export SGX_SIGNER_KEY=/root/.config/gramine/enclave-key.pem

    # mkdir and make
    if [ ! -d "/gramine/leader" ] || [ ! -d "/gramine/follower" ]; then
        mkdir -p /gramine/leader
        mkdir -p /gramine/follower
        need_clean=1
    fi
    make all > /dev/null
    if [ $? -eq 0 ]; then
        gramine-sgx-get-token -s python.sig -o /dev/null
    fi

    # clean
    make clean > /dev/null
    if [ $need_clean==1 ]; then
        rm -rf /gramine/leader
        rm -rf /gramine/follower
    fi
    cd -
}

get_token