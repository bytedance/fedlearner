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

IMAGE_HUB_URL=$1
IMAGE_HUB_USERNAME=$2
IMAGE_HUB_PASSWORD=$3
EXTERNAL_NAME=$4
GRPC_SSL_NAME=$5
DB_PASSWORD=$6
DOMAIN_URL=$7

REGION="cn-beijing"
ZONE_ID="cn-beijing-h"
GENERATER_NAME="fedlearnerwins"

function echo_exit {
    echo $1
    exit 1
}

function json2yaml {
    python -c 'import json; open("config", "w").write(json.load(open("./tmp","r"))["config"]);'
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
    echo "    ./upgrade-add-on.sh image_hub_url image_hub_username image_hub_password external_name grpc_ssl_name db_password domain_url"
    echo ""
    echo "Params:"
    echo ""
    echo "    image_hub_url:      the docker image hub url, required"
    echo "    image_hub_username: the docker image hub username, required"
    echo "    image_hub_password: the docker image hub password, required"
    echo "    external_name:      the ip address for external service, required"
    echo "    grpc_ssl_name:      the grpc ssl name, required"
    echo "    db_password:        the database password, required"
    echo "    domain_url:         the domain url, required"
}

if [[ -z $IMAGE_HUB_URL ]] || [[ -z $IMAGE_HUB_USERNAME ]] || [[ -z $IMAGE_HUB_PASSWORD ]] || [[ -z $EXTERNAL_NAME  ]] || [[ -z $GRPC_SSL_NAME ]] || [[ -z $DOMAIN_URL ]]
then
    usage
    exit 1
else
    upgrade
fi
