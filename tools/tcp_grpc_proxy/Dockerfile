FROM golang:1.16

RUN apt-get update && \
    apt install -y curl git vim && \
    apt-get install -y make nginx g++ libgmp-dev libglib2.0-dev libssl-dev && \
    apt-get install -y protobuf-compiler && \
    apt-get clean

WORKDIR /app
COPY . /app/tcp_grpc_proxy

# Copies PSI lib
RUN git clone --recursive git://github.com/encryptogroup/PSI

WORKDIR /app/PSI
RUN make

WORKDIR /app/tcp_grpc_proxy
RUN make build

# upgrade nginx
RUN echo "deb http://nginx.org/packages/mainline/debian/ stretch nginx deb-src http://nginx.org/packages/mainline/debian/ stretch nginx" > /etc/apt/sources.list.d/nginx.list
RUN wget -qO - https://nginx.org/keys/nginx_signing.key | apt-key add -
RUN apt update && \
    apt remove nginx-common -y && \
    apt install nginx
