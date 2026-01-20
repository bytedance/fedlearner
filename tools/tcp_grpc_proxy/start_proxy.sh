#! /bin/bash
set -ex

# The chain of the traffic:
# TCP client -> out TCP server -> out gRPC server -> Nginx ->
# network -> remote grpc server (Nginx) -> in gRPC server -> in TCP server
OUT_TCP_SERVER_PORT=17767
OUT_GRPC_SERVER_PORT=17768
IN_GRPC_SERVER_PORT=17769
IN_TCP_SERVER_PORT=7766

REMOTE_GRPC_SERVER_HOST=1.1.1.1
REMOTE_GRPC_SERVER_PORT=17771

echo "
upstream remote_grpc_server {
    server ${REMOTE_GRPC_SERVER_HOST}:${REMOTE_GRPC_SERVER_PORT};
}

# Proxies to remote grpc server
server {
    listen ${OUT_GRPC_SERVER_PORT} http2;

    # No limits
    client_max_body_size 0;
    grpc_read_timeout 3600s;
    grpc_send_timeout 3600s;
    client_body_timeout 3600s;
    # grpc_socket_keepalive is recommended but not required
    # grpc_socket_keepalive is supported after nginx 1.15.6
    grpc_socket_keepalive on;
    location / {
        # change grpc to grpcs if ssl is used
        grpc_pass grpc://remote_grpc_server;
    }
}

# Listens grpc traffic, this port should be public
server {
    listen ${REMOTE_GRPC_SERVER_PORT} http2;

    # No limits
    client_max_body_size 0;
    grpc_read_timeout 3600s;
    grpc_send_timeout 3600s;
    client_body_timeout 3600s;
    grpc_socket_keepalive on;
    location / {
        grpc_pass grpc://localhost:${IN_GRPC_SERVER_PORT};
    }
}
" > nginx.conf
cp nginx.conf /etc/nginx/conf.d/nginx.conf
service nginx restart

./tcp2grpc --tcp_server_port="$OUT_TCP_SERVER_PORT" \
           --target_grpc_address="localhost:$OUT_GRPC_SERVER_PORT" &

./grpc2tcp --grpc_server_port="$IN_GRPC_SERVER_PORT" \
           --target_tcp_address="localhost:$IN_TCP_SERVER_PORT" &
