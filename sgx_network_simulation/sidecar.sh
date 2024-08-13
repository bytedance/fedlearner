#!/bin/bash
set -ex

LISTEN_PORT_PATH="/pod-data/listen_port"
while [ ! -s "$LISTEN_PORT_PATH" ]; do
  echo "wait for $LISTEN_PORT_PATH ..."
  sleep 1
done
WORKER_LISTEN_PORT=$(cat "$LISTEN_PORT_PATH")

PROXY_LOCAL_PORT_PATH="/pod-data/proxy_local_port"
while [ ! -s "$PROXY_LOCAL_PORT_PATH" ]; do
  echo "wait for $PROXY_LOCAL_PORT_PATH ..."
  sleep 1
done
PROXY_LOCAL_PORT=$(cat "$PROXY_LOCAL_PORT_PATH")

GRPC_SERVER_PORT=32001
if [ -n "$PORT0" ]; then
  GRPC_SERVER_PORT=$PORT0
fi

TARGET_GRPC_PORT=32102
if [ -n "$PORT1" ]; then
  TARGET_GRPC_PORT=$PORT1
fi

echo "# Forwards all traffic to nginx controller
server {
    listen ${TARGET_GRPC_PORT} http2;

    # No limits
    client_max_body_size 0;
    grpc_read_timeout 3600s;
    grpc_send_timeout 3600s;
    client_body_timeout 3600s;
    # grpc_socket_keepalive is recommended but not required
    # grpc_socket_keepalive is supported after nginx 1.15.6
    grpc_socket_keepalive on;

    grpc_set_header Authority ${EGRESS_HOST};
    grpc_set_header Host ${EGRESS_HOST};
    grpc_set_header X-Host ${SERVICE_ID}.${EGRESS_DOMAIN};

    location / {
        # Redirects to nginx controller
        grpc_pass grpc://fedlearner-stack-ingress-nginx-controller.default.svc:80;
    }
}
" > nginx/sidecar.conf

rm -rf /etc/nginx/conf.d/*
cp nginx/sidecar.conf /etc/nginx/conf.d/
service nginx restart

# Server sidecar: grpc to tcp, 5001 is the server port of main container
echo "Starting server sidecar"
./grpc2tcp --grpc_server_port=$GRPC_SERVER_PORT \
           --target_tcp_address="localhost:$WORKER_LISTEN_PORT" &

echo "Starting client sidecar"
./tcp2grpc --tcp_server_port="$PROXY_LOCAL_PORT" \
           --target_grpc_address="localhost:$TARGET_GRPC_PORT" &

echo "===========Sidecar started!!============="

while true
do
  if [[ -f "/pod-data/main-terminated" ]]
  then
    exit 0
  fi
  sleep 5
done
