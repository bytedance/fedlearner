#!/bin/bash
set -ex

TF_CFLAGS=$(python -c 'import tensorflow.compat.v1 as tf; print(" ".join(tf.sysconfig.get_compile_flags()))')
TF_LFLAGS=$(python -c 'import tensorflow.compat.v1 as tf; print(" ".join(tf.sysconfig.get_link_flags()))')

SRC_DIR=$(pwd)/cc

g++ -std=c++11 -shared ${SRC_DIR}/operators/kernels/*.cc ${SRC_DIR}/operators/ops/*.cc -o ${SRC_DIR}/embedding.so -fPIC ${TF_CFLAGS} ${TF_LFLAGS} -O2
