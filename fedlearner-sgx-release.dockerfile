FROM fedlearner-sgx-dev:latest AS builder

RUN rm -rf /tf /grpc/*build

RUN unset PWD HOSTNAME

RUN env && env > ~/.env && sed -i "s/^/export ${i}\t&/g" ~/.env && echo "source ~/.env" >> ~/.bashrc

FROM scratch

COPY --from=builder / /

