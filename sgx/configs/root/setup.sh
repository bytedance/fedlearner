#!/bin/bash
set -e
set -x

# graphene
openssl genrsa -3 -out ${SGX_SIGNER_KEY} 3072

# ${GRAPHENEDIR}/Examples/ra-tls-secret-prov/build.sh
# ${GRAPHENEDIR}/Examples/ra-tls-mbedtls/build_install.sh

# grpc
# ${GRPC_PATH}/build_install.sh

# fedlearner
# ${FEDLEARNER_PATH}/build_install.sh

# others
#apt-get install -y lsb-release strace gdb ctags curl zip vim

# echo "alias tensorboard=\"python3 /usr/local/bin/python3.6.9/lib/python3.6/site-packages/tensorboard/main.py\"" >> ~/.bashrc
# tensorboard --logdir=/tmp/tf-log --host 0.0.0.0 --port 6006 &
