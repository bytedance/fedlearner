#!/bin/bash
# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

EIP=$1
NAME=$2

function add_customer {
    kubectl get service $NAME -n ingress-nginx >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
        echo "The ingress was already created."
    else
        cat <<EOF > ingress.yml
apiVersion: v1
kind: Service
metadata:
  name: $NAME
  namespace: ingress-nginx
spec:
  externalName: $EIP
  type: ExternalName
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/backend-protocol: GRPCS
    nginx.ingress.kubernetes.io/configuration-snippet: |
      grpc_set_header  Authority \$http_x_host;
      grpc_set_header  Host \$http_x_host;
    nginx.ingress.kubernetes.io/http2-insecure-port: "true"
  name: $NAME
  namespace: ingress-nginx
spec:
  rules:
  - host: $NAME.com
    http:
      paths:
      - backend:
          serviceName: $NAME
          servicePort: 32443
        path: /
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/backend-protocol: GRPCS
    nginx.ingress.kubernetes.io/configuration-snippet: |
      grpc_set_header  Authority \$http_x_host;
      grpc_set_header  Host \$http_x_host;
      grpc_next_upstream_tries 5;
    nginx.ingress.kubernetes.io/http2-insecure-port: "true"
    nginx.ingress.kubernetes.io/server-snippet: |
      grpc_ssl_verify on;
      grpc_ssl_name \$http_x_host;
      grpc_ssl_server_name on;
      grpc_ssl_trusted_certificate /etc/ingress-nginx/client/intermediate.pem;
      grpc_ssl_certificate  /etc/ingress-nginx/client/client.pem;
      grpc_ssl_certificate_key  /etc/ingress-nginx/client/client.key;
  name: $NAME-client-auth
  namespace: ingress-nginx
spec:
  rules:
  - host: $NAME-client-auth.com
    http:
      paths:
      - backend:
          serviceName: $NAME
          servicePort: 32443
        path: /
EOF

        kubectl create -f ingress.yml
    fi
}

function usage {
    echo "Usage: "
    echo "    ./add_customer.sh eip name"
    echo ""
    echo "Params:"
    echo ""
    echo "    eip:  the eip of SLB in aliyun, required"
    echo "    name: the name of domain with \".com\" removed, required"
}

if [[ -z $EIP ]] || [[ -z $NAME ]]
then
    usage
    exit 1
else
    add_customer
fi
