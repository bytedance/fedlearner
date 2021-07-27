# https://github.com/oscarlab/graphene/blob/master/Tools/gsc/images/graphene_aks.latest.dockerfile

FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

#COPY configs/etc/apt/sources.list /etc/apt/sources.list

# Add steps here to set up dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends apt-utils \
    && apt-get install -y \
        build-essential \
        autoconf \
        libtool \
        python3-pip \
        python3-dev \
        git \
        wget

# Intel SGX
RUN echo "deb [trusted=yes arch=amd64] https://download.01.org/intel-sgx/sgx_repo/ubuntu bionic main" | tee /etc/apt/sources.list.d/intel-sgx.list \
    && wget -qO - https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key | apt-key add - \
    && apt-get update

# Install SGX-PSW
RUN apt-get install -y libsgx-pce-logic libsgx-ae-qve libsgx-quote-ex libsgx-qe3-logic sgx-aesm-service

# Install SGX-DCAP
RUN apt-get install -y libsgx-dcap-ql-dev libsgx-dcap-default-qpl libsgx-dcap-quote-verify-dev

# Graphene
ENV GRAPHENEDIR=/graphene
ENV GRAPHENE_VERSION=2fdb529f81e839ef1d9638362c2c02a4e34af79f
# ENV GRAPHENE_VERSION=master
ENV ISGX_DRIVER_PATH=${GRAPHENEDIR}/Pal/src/host/Linux-SGX/linux-sgx-driver
ENV SGX_SIGNER_KEY=${GRAPHENEDIR}/Pal/src/host/Linux-SGX/signer/enclave-key.pem
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8
ENV WERROR=1
ENV SGX=1

# https://graphene.readthedocs.io/en/latest/building.html
# golang is needed by grpc/BoringSSL
RUN apt-get install -y gawk bison meson python3-click python3-jinja2 golang
RUN apt-get install -y libcurl4-openssl-dev libprotobuf-c-dev python3-protobuf protobuf-c-compiler
RUN pip3 install toml>=0.10

RUN git clone https://github.com/oscarlab/graphene.git ${GRAPHENEDIR} \
    && cd ${GRAPHENEDIR} \
    && git checkout ${GRAPHENE_VERSION}

# Create SGX driver for Graphene
RUN git clone https://github.com/intel/SGXDataCenterAttestationPrimitives.git ${ISGX_DRIVER_PATH} \
    && cd ${ISGX_DRIVER_PATH} \
    && git checkout DCAP_1.9 \
    && cp -r driver/linux/* ${ISGX_DRIVER_PATH}

# Build Graphene with SGX
# https://graphene.readthedocs.io/en/latest/quickstart.html#quick-start-with-sgx-support
RUN cd ${GRAPHENEDIR} \
    && make -j `nproc` ISGX_DRIVER_PATH="" SGX=0 \
    && make -j `nproc` \
    && meson build -Ddirect=enabled -Dsgx=enabled \
    && ninja -C build \
    && ninja -C build install

# Translate runtime symlinks to files
RUN for f in $(find ${GRAPHENEDIR}/Runtime -type l); do cp --remove-destination $(realpath $f) $f; done

## Fedlearner
#ENV FEDLEARNER_PATH=/fedlearner
#ENV FEDLEARNER_VERSION=master
## ENV FEDLEARNER_VERSION=5cce3c1fe09abe66879274a0ad3dc8e2f25a322d
#
#RUN apt-get install -y libgmp-dev libmpfr-dev libmpc-dev libmysqlclient-dev
#
#RUN git clone https://github.com/bytedance/fedlearner.git --recursive ${FEDLEARNER_PATH} \
#    && cd ${FEDLEARNER_PATH} \
#    && git checkout ${FEDLEARNER_VERSION}
#
#RUN pip3 install --upgrade pip setuptools \
#    && ln -s /usr/bin/python3 /usr/bin/python \
#    && pip3 install -r ${FEDLEARNER_PATH}/requirements.txt

# GRPC
ENV GRPC_PATH=/grpc
ENV INSTALL_PREFIX=/usr/local
ENV LD_LIBRARY_PATH=${INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}
ENV PATH=${INSTALL_PREFIX}/bin:${LD_LIBRARY_PATH}:${PATH}

RUN mkdir -p ${INSTALL_PREFIX} \
    && wget -q -O cmake-linux.sh https://github.com/Kitware/CMake/releases/download/v3.19.6/cmake-3.19.6-Linux-x86_64.sh \
    && sh cmake-linux.sh -- --skip-license --prefix=${INSTALL_PREFIX} \
    && rm cmake-linux.sh

RUN git clone --recurse-submodules -b v1.38.1 https://github.com/grpc/grpc ${GRPC_PATH}
COPY grpc ${GRPC_PATH}

RUN cd ${GRPC_PATH} \
    && pip3 install --upgrade pip setuptools==44.1.1 \
    && pip3 install -r requirements.txt

COPY grpc/build_install.sh ${GRPC_PATH}
RUN ${GRPC_PATH}/build_install.sh

COPY graphene ${GRAPHENEDIR}
COPY fedlearner ${FEDLEARNER_PATH}
#COPY grpc ${GRPC_PATH}
COPY configs /

# Temp setup script
RUN chmod +x /root/setup.sh \
    && /root/setup.sh

# https://askubuntu.com/questions/93457/how-do-i-enable-or-disable-apport
RUN echo "enabled=0" > /etc/default/apport
RUN echo "exit 0" > /usr/sbin/policy-rc.d

# Clean tmp files
RUN apt-get clean all \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache/pip/* \
    && rm -rf /tmp/*

# Workspace
ENV WORK_SPACE_PATH=${GRAPHENEDIR}
WORKDIR ${WORK_SPACE_PATH}

EXPOSE 6006 50051 50052

RUN chmod +x /root/entrypoint.sh
# ENTRYPOINT ["/root/entrypoint.sh"]
