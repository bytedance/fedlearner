#!/bin/bash
set -ex

FILE_PATH="/pod-data/listen_port"
while [ ! -s "$FILE_PATH" ]; do
  echo "wait for $FILE_PATH ..."
  sleep 1
done
WORKER_LISTEN_PORT=$(cat "$FILE_PATH")

echo "# Forwards all traffic to nginx controller
server {
    listen 32102 http2;

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

if [ -z "$PORT0" ]; then
  PORT0=32001
fi

if [ -z "$PORT2" ]; then
  PORT2=32102
fi

sed -i "s/listen [0-9]* http2;/listen $PORT2 http2;/" nginx/sidecar.conf

cp nginx/sidecar.conf /etc/nginx/conf.d/
service nginx restart

# Server sidecar: grpc to tcp, 5001 is the server port of main container
echo "Starting server sidecar"
./grpc2tcp --grpc_server_port=$PORT0 \
           --target_tcp_address="localhost:$WORKER_LISTEN_PORT" &

echo "Starting client sidecar"
./tcp2grpc --tcp_server_port="$PROXY_LOCAL_PORT" \
           --target_grpc_address="localhost:$PORT2" &

echo "===========Sidecar started!!============="

while true
do
  if [[ -f "/pod-data/main-terminated" ]]
  then
    exit 0
  fi
  sleep 5
done
