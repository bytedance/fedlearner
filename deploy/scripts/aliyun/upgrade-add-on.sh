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

ACCESS_KEY_ID=$1
ACCESS_KEY_SECRET=$2
IMAGE_HUB_URL=$3
IMAGE_HUB_USERNAME=$4
IMAGE_HUB_PASSWORD=$5
EXTERNAL_NAME=$6
GRPC_SSL_NAME=$7
DB_PASSWORD=$8
DOMAIN_URL=$9

REGION="cn-beijing"
ZONE_ID="cn-beijing-h"
GENERATER_NAME="fedlearnerwins"

function echo_exit {
    echo $1
    exit 1
}

function echo_log {
    msg=$1
    echo $msg
    echo $msg >> upgrade.log
}

function json2yaml {
    python -c 'import json; open("config", "w").write(json.load(open("./tmp","r"))["config"]);'
}

function install_cli {
    # Download kubectl
    kubectl help >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo_log "Download kubectl."
        curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.18.0/bin/darwin/amd64/kubectl
        mv kubectl /usr/local/bin/
        chmod 755 /usr/local/bin/kubectl
    fi

    # Download helm
    helm version | grep Version:\"v3 >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo_log "Download helm."
        curl -LO https://get.helm.sh/helm-v3.2.3-darwin-amd64.tar.gz
        tar -zxvf helm-v3.2.3-darwin-amd64.tar.gz
        mv darwin-amd64/helm /usr/local/bin/
        chmod 755 /usr/local/bin/helm
        rm -rf darwin-amd64 helm-v3.2.3-darwin-amd64.tar.gz
    fi

    # Download aliyun cli
    aliyun version >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo_log "Download aliyun cli."
        curl -LO https://aliyuncli.alicdn.com/aliyun-cli-macosx-3.0.32-amd64.tgz
        tar -zxvf aliyun-cli-macosx-3.0.32-amd64.tgz
        mv aliyun /usr/local/bin
        chmod 755 /usr/local/bin/aliyun
        rm -rf aliyun-cli-macosx-3.0.32-amd64.tgz
    fi

    # Configure aliyun cli
    aliyun auto-completion
    aliyun configure set --profile akProfile --region $REGION --access-key-id $ACCESS_KEY_ID --access-key-secret $ACCESS_KEY_SECRET --language en
    if [ $? -ne 0 ]
    then
        echo_exit "Failed to initiate aliyun cli."
    fi
}

function upgrade {
    cat ../../charts/fedlearner-add-on/configuration-snippet.txt | grep grpc_set_header >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo "grpc_set_header Host $GRPC_SSL_NAME;" >> ../../charts/fedlearner-add-on/configuration-snippet.txt
    fi

    cat ../../charts/fedlearner-add-on/server-snippet.txt | grep grpc_ssl_name >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo "grpc_ssl_name $GRPC_SSL_NAME;" >> ../../charts/fedlearner-add-on/server-snippet.txt
    fi

    CLUSTER_ID=`aliyun cs DescribeClusters | grep -A 1 name | grep -A 1 $GENERATER_NAME | grep cluster_id | awk -F "\"" '{print $4}'`
    if [ $? -ne 0 ]
    then
        echo_exit "Failed to get k8s cluster."
    fi

    rm -rf tmp config
    echo "Creating config file in current dir, you can move it to ~/.kube/config."
    aliyun cs GET /k8s/$CLUSTER_ID/user_config > ./tmp
    if [ $? -ne 0 ]
    then
        echo_exit "Failed to get k8s cluster config."
    fi

    json2yaml
    CURRENT_DIR=`pwd`
    export KUBECONFIG="$CURRENT_DIR/config"

    helm upgrade fedlearner-add-on ../../charts/fedlearner-add-on \
        --set imageCredentials.registry=$IMAGE_HUB_URL \
        --set imageCredentials.username=$IMAGE_HUB_USERNAME \
        --set imageCredentials.password=$IMAGE_HUB_PASSWORD \
        --set service.externalName=$EXTERNAL_NAME

    FILE_SYSTEM_ID=`aliyun nas DescribeFileSystems --Description $GENERATER_NAME | grep FileSystemId | awk -F "\"" '{print $4}'`
    if [ -n "$FILE_SYSTEM_ID" ]
    then
        MOUNT_TARGET_DOMAIN=`aliyun nas DescribeMountTargets --FileSystemId $FILE_SYSTEM_ID | grep MountTargetDomain | awk -F "\"" '{print $4}'`
        helm upgrade fedlearner-stack ../../charts/fedlearner-stack --set nfs-server-provisioner.enabled=false \
            --set nfs-client-provisioner.enabled=true \
            --set nfs-client-provisioner.nfs.server=$MOUNT_TARGET_DOMAIN \
            --set mariadb.enabled=false \
            --set 'ingress-nginx.controller.extraVolumeMounts[0].name=fedlearner-proxy-client' \
            --set 'ingress-nginx.controller.extraVolumeMounts[0].mountPath=/etc/ingress-nginx/client/' \
            --set 'ingress-nginx.controller.extraVolumes[0].name=fedlearner-proxy-client' \
            --set 'ingress-nginx.controller.extraVolumes[0].secret.secretName=fedlearner-proxy-client'
    else
        echo_exit "Failed to update fedlearner-stack since missing MOUNT_TARGET_DOMAIN."
    fi

    VPC_ID=`aliyun vpc DescribeVpcs --VpcName $GENERATER_NAME | grep VpcId | awk -F "\"" '{print $4}'`
    if [[ $VPC_ID == "vpc"* ]]
    then
        DB_INSTANCE_ID=`aliyun rds DescribeDBInstances --VpcId $VPC_ID | grep \"DBInstanceId\" | awk -F "\"" '{print $4}'`
        if [ -n "$DB_INSTANCE_ID" ]
        then
            DB_URL=`aliyun rds DescribeDBInstanceNetInfo --DBInstanceId $DB_INSTANCE_ID | grep ConnectionString\" | awk -F "\"" '{print $4}'`
            helm upgrade fedlearner ../../charts/fedlearner \
                --set fedlearner-web-console.cluster.env.DB_USERNAME=fedlearner \
                --set fedlearner-web-console.cluster.env.DB_PASSWORD=$DB_PASSWORD \
                --set fedlearner-web-console.cluster.env.DB_HOST=$DB_URL \
                --set fedlearner-web-console.cluster.env.DB_PORT=3306 \
                --set fedlearner-operator.extraArgs.ingress-extra-host-suffix=$DOMAIN_URL \
                --set fedlearner-operator.extraArgs.ingress-client-auth-secret-name="default/ca-secret" \
                --set fedlearner-operator.extraArgs.ingress-enabled-client-auth=true \
                --set fedlearner-operator.extraArgs.ingress-secret-name=fedlearner-proxy-server
        else
            echo_exit "Failed to update fedlearner-stack since missing DB_INSTANCE_ID."
        fi
    else
        echo_exit "Failed to update fedlearner-stack since missing VPC_ID."
    fi
}

function usage {
    echo "Usage: "
    echo "    ./upgrade-add-on.sh access_key_id access_key_secret image_hub_url image_hub_username image_hub_password external_name grpc_ssl_name db_password domain_url"
    echo ""
    echo "Params:"
    echo ""
    echo "    access_key_id:     the access key id provided by aliyun, required"
    echo "    access_key_secret: the access key secret provided by aliyun, required"
    echo "    image_hub_url:      the docker image hub url, required"
    echo "    image_hub_username: the docker image hub username, required"
    echo "    image_hub_password: the docker image hub password, required"
    echo "    external_name:      the ip address for external service, required"
    echo "    grpc_ssl_name:      the grpc ssl name, required"
    echo "    db_password:        the database password, required"
    echo "    domain_url:         the domain url, required"
}

if [[ -z $ACCESS_KEY_ID ]] || [[ -z $ACCESS_KEY_SECRET ]] || [[ -z $IMAGE_HUB_URL ]] || [[ -z $IMAGE_HUB_USERNAME ]] || [[ -z $IMAGE_HUB_PASSWORD ]] || [[ -z $EXTERNAL_NAME  ]] || [[ -z $GRPC_SSL_NAME ]] || [[ -z $DOMAIN_URL ]]
then
    usage
    exit 1
else
    install_cli
    upgrade
fi
