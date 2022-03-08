ARG base_image=fedlearner-sgx-dev:latest

FROM ${base_image} AS builder

RUN cp /grpc/examples/dynamic_config.json /tmp

RUN rm -rf /tf /grpc

RUN mkdir -p /grpc/examples && mv /tmp/dynamic_config.json /grpc/examples

RUN unset PWD HOSTNAME http_proxy https_proxy

RUN env && env > ~/.env && sed -i "s/^/export ${i}\t&/g" ~/.env && echo "source ~/.env" >> ~/.bashrc

FROM scratch

COPY --from=builder / /
