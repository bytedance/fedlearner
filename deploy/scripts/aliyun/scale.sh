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

INSTANCE_TYPE=$1

REGION="cn-beijing"
ZONE_ID="cn-beijing-h"
GENERATER_NAME="fedlearnerwins"

function init_para {
    CLUSTER_ID=`aliyun cs DescribeClusters |grep -A 1 name |grep -A 1 $GENERATER_NAME |grep cluster_id |awk -F "\"" '{print $4}'`
}

function list_k8s_nodes {
    NODES=`aliyun ecs DescribeInstances --InstanceName worker-k8s-for-cs-$CLUSTER_ID | grep InstanceId | awk -F "\"" '{print $4}'`
    if [ -n "$NODES" ]
    then
        echo "Kubernetes cluster has following nodes:"
        echo $NODES
    else
        echo "Failed to list the k8s nodes with name worker-k8s-for-cs-$CLUSTER_ID"
    fi
}

function scale {
    for node in $NODES
    do
        aliyun ecs StopInstance --InstanceId $node --ForceStop true
        sleep 30
        echo "Resize instance $node to $INSTANCE_TYPE."
        aliyun ecs ModifyInstanceSpec --InstanceId $node --InstanceType $INSTANCE_TYPE
        sleep 30 
        aliyun ecs StartInstance --InstanceId $node
    done
}

function usage {
    echo "Usage: "
    echo "    ./scale.sh instance_type"
    echo ""
    echo "Params:"
    echo ""
    echo "    instance_type: the instance type, required"
    echo ""
    echo "Instance type referrence."
    echo "- ecs.s6-c1m2.xlarge:  4c8g"
    echo "- ecs.s6-c1m2.2xlarge: 8c16g"
    echo "- ecs.c6e.4xlarge:     16c32g"
    echo "- ecs.c6e.8xlarge:     32c64g"
}

if [[ -z $INSTANCE_TYPE ]]
then
    usage
    exit 1
else
    init_para
    list_k8s_nodes
    scale
fi
