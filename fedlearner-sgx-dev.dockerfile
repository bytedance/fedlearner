# https://github.com/gramineproject/gramine/blob/master/.ci/ubuntu18.04.dockerfile

FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
ENV INSTALL_PREFIX=/usr/local
ENV LD_LIBRARY_PATH=${INSTALL_PREFIX}/lib:${INSTALL_PREFIX}/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}
ENV PATH=${INSTALL_PREFIX}/bin:${LD_LIBRARY_PATH}:${PATH}

# Add steps here to set up common dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends apt-utils \
    && apt-get install -y \
        ca-certificates \
        build-essential \
        autoconf \
        libtool \
        python3-pip \
        python3-dev \
        git \
        wget \
        unzip \
        zlib1g-dev \
        jq

# Intel SGX PPA
RUN echo "deb [trusted=yes arch=amd64] https://download.01.org/intel-sgx/sgx_repo/ubuntu bionic main" | tee /etc/apt/sources.list.d/intel-sgx.list \
    && wget -qO - https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key | apt-key add - \
    && apt-get update

# Install SGX-PSW
RUN apt-get install -y libsgx-pce-logic libsgx-ae-qve libsgx-quote-ex libsgx-quote-ex libsgx-quote-ex-dev libsgx-qe3-logic sgx-aesm-service

# Install SGX-DCAP
RUN apt-get install -y libsgx-dcap-ql-dev libsgx-dcap-default-qpl libsgx-dcap-quote-verify-dev libsgx-dcap-default-qpl-dev

# Install CMAKE
RUN mkdir -p ${INSTALL_PREFIX} \
    && wget -q -O cmake-linux.sh https://github.com/Kitware/CMake/releases/download/v3.19.6/cmake-3.19.6-Linux-x86_64.sh \
    && sh cmake-linux.sh -- --skip-license --prefix=${INSTALL_PREFIX} \
    && rm cmake-linux.sh

# Install gramine
ENV GRAMINEDIR=/gramine
ENV SGX_DCAP_VERSION=DCAP_1.11
# ENV GRAPHENE_VERSION=master
# ENV GRAMINE_VERSION=497847c0353a13c9e83c0ec4c0cbe99f11d4a75d
ENV GRAMINE_VERSION=c662f63bba76736e6d5122a866da762efd1978c1
ENV ISGX_DRIVER_PATH=${GRAMINEDIR}/driver
ENV SGX_SIGNER_KEY=${GRAMINEDIR}/Pal/src/host/Linux-SGX/signer/enclave-key.pem
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8
ENV WERROR=1
ENV SGX=1

# https://gramine.readthedocs.io/en/latest/building.html
# golang is needed by grpc/BoringSSL
RUN apt-get install -y gawk bison python3-click python3-jinja2 golang ninja-build
RUN apt-get install -y libcurl4-openssl-dev libprotobuf-c-dev python3-protobuf protobuf-c-compiler
RUN apt-get install -y libgmp-dev libmpfr-dev libmpc-dev libisl-dev

RUN ln -s /usr/bin/python3 /usr/bin/python \
    && pip3 install --upgrade pip \
    && pip3 install toml meson

RUN git clone https://github.com/gramineproject/gramine.git ${GRAMINEDIR} \
    && cd ${GRAMINEDIR} \
    && git checkout ${GRAMINE_VERSION}

RUN git clone https://github.com/intel/SGXDataCenterAttestationPrimitives.git ${ISGX_DRIVER_PATH} \
    && cd ${ISGX_DRIVER_PATH} \
    && git checkout ${SGX_DCAP_VERSION}

COPY sgx/gramine/patches ${GRAMINEDIR}
RUN cd ${GRAMINEDIR} \
    && git apply *.diff

# https://gramine.readthedocs.io/en/latest/quickstart.html#quick-start-with-sgx-support
RUN openssl genrsa -3 -out ${SGX_SIGNER_KEY} 3072
RUN cd ${GRAMINEDIR} \
    && LD_LIBRARY_PATH="" meson setup build/ --buildtype=release -Dprefix=${INSTALL_PREFIX} -Ddirect=enabled -Dsgx=enabled -Ddcap=enabled -Dsgx_driver=dcap1.10 -Dsgx_driver_include_path=${ISGX_DRIVER_PATH}/driver/linux/include \
    && LD_LIBRARY_PATH="" ninja -C build/ \
    && LD_LIBRARY_PATH="" ninja -C build/ install

# Install mbedtls
RUN cd ${GRAMINEDIR}/build/subprojects/mbedtls-mbedtls* \
    && cp -r `find . -name "*_gramine.a"` ${INSTALL_PREFIX}/lib \
    && cp -r ${GRAMINEDIR}/subprojects/mbedtls-mbedtls*/include ${INSTALL_PREFIX}

# Install cJSON
RUN cd ${GRAMINEDIR}/subprojects/cJSON* \
    && make static \
    && cp -r *.a ${INSTALL_PREFIX}/lib \
    && mkdir -p ${INSTALL_PREFIX}/include/cjson \
    && cp -r *.h ${INSTALL_PREFIX}/include/cjson

# GRPC dependencies
ENV GRPC_PATH=/grpc
ENV GRPC_VERSION=v1.38.1
# ENV GRPC_VERSION=b54a5b338637f92bfcf4b0bc05e0f57a5fd8fadd

RUN git clone --recurse-submodules -b ${GRPC_VERSION} https://github.com/grpc/grpc ${GRPC_PATH}

RUN pip3 install --upgrade pip \
    && pip3 install -r ${GRPC_PATH}/requirements.txt

# Tensorflow dependencies
ENV BAZEL_VERSION=3.1.0
ENV TF_VERSION=v2.4.2
ENV TF_BUILD_PATH=/tf/src
ENV TF_BUILD_OUTPUT=/tf/output

RUN pip3 install --upgrade pip \
    && pip3 install numpy keras_preprocessing

RUN wget "https://github.com/bazelbuild/bazel/releases/download/${BAZEL_VERSION}/bazel_${BAZEL_VERSION}-linux-x86_64.deb" \
    && dpkg -i bazel_*.deb

RUN git clone --recurse-submodules -b ${TF_VERSION} https://github.com/tensorflow/tensorflow ${TF_BUILD_PATH}

# Fedlearner dependencies
ENV FEDLEARNER_PATH=/fedlearner

RUN apt-get install -y libmysqlclient-dev

# Build gRPC 
COPY sgx/grpc/common ${GRPC_PATH}
COPY sgx/grpc/v1.38.1 ${GRPC_PATH}

RUN ${GRPC_PATH}/build_python.sh

# Build tensorflow
COPY sgx/tf ${TF_BUILD_PATH}

RUN cd ${TF_BUILD_PATH} \
    && git apply sgx_tls_sample.diff

ARG TF_BUILD_CFG="--config=numa --config=mkl --config=mkl_threadpool --copt=-march=native --copt=-O3 --cxxopt=-march=native --cxxopt=-O3 --cxxopt=-D_GLIBCXX_USE_CXX11_ABI=0"
RUN cd ${TF_BUILD_PATH} \
    && bazel build -c opt ${TF_BUILD_CFG} //tensorflow/tools/pip_package:build_pip_package \
    && bazel-bin/tensorflow/tools/pip_package/build_pip_package ${TF_BUILD_OUTPUT}

# Build and install fedlearner
COPY . ${FEDLEARNER_PATH}

RUN pip3 install --upgrade pip \
    && pip3 install -r ${FEDLEARNER_PATH}/requirements.txt

RUN cd ${FEDLEARNER_PATH} \
    && make protobuf \
    && python3 setup.py bdist_wheel \
    && pip3 install ./dist/*.whl

# Re-install tensorflow, uninstall tensorflow_io, mock it
RUN pip3 uninstall -y tensorflow tensorflow-io \
    && pip3 install ${TF_BUILD_OUTPUT}/*.whl

# Re-install fedlearner plugin
RUN cd ${FEDLEARNER_PATH} \
    && make op \
    && mkdir -p /usr/local/lib/python3.6/dist-packages/cc \
    && cp ./cc/embedding.so /usr/local/lib/python3.6/dist-packages/cc

# Re-install grpcio
RUN pip3 uninstall -y grpcio \
    && pip3 install ${GRPC_PATH}/dist/grpcio*.whl

# For debug
RUN apt-get install -y strace gdb ctags vim

COPY sgx/gramine/CI-Examples ${GRAMINEDIR}/CI-Examples
COPY sgx/configs /

# https://askubuntu.com/questions/93457/how-do-i-enable-or-disable-apport
RUN echo "enabled=0" > /etc/default/apport
RUN echo "exit 0" > /usr/sbin/policy-rc.d

# Clean tmp files
RUN apt-get clean all \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache/* \
    && rm -rf /tmp/*

# Workspace
ENV WORK_SPACE_PATH=${GRAMINEDIR}
WORKDIR ${WORK_SPACE_PATH}

EXPOSE 6006 50051 50052

RUN chmod +x /root/entrypoint.sh
# ENTRYPOINT ["/root/entrypoint.sh"]
