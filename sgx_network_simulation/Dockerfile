FROM golang:1.16 AS go

RUN apt-get update && \
    apt-get install -y make g++ libgmp-dev libglib2.0-dev libssl-dev && \
    apt-get install -y protobuf-compiler && \
    apt-get clean

WORKDIR /app
COPY tools/tcp_grpc_proxy ./
RUN make build

FROM python:3.6.8

RUN echo "deb http://archive.debian.org/debian stretch main contrib non-free" > /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y curl vim make nginx && \
    apt-get clean

# upgrade nginx
RUN echo "deb http://nginx.org/packages/mainline/debian/ stretch nginx deb-src http://nginx.org/packages/mainline/debian/ stretch nginx" > /etc/apt/sources.list.d/nginx.list
RUN wget -qO - https://nginx.org/keys/nginx_signing.key | apt-key add -
RUN apt update && \
    apt remove nginx-common -y && \
    apt install nginx

COPY sgx_network_simulation/ /app/
WORKDIR /app
COPY --from=go /app/tcp2grpc ./
COPY --from=go /app/grpc2tcp ./
