#!/bin/bash

cd /gramine/CI-Examples/generate-token/
make clean > /dev/null
export SGX=1
export SGX_SIGNER_KEY=/root/.config/gramine/enclave-key.pem
make all > /dev/null
if [ $? -eq 0 ]; then
    gramine-sgx-get-token -s python.sig -o /dev/null
fi
make clean > /dev/null