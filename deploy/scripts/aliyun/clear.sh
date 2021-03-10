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

REGION="cn-beijing"
ZONE_ID="cn-beijing-h"
GENERATER_NAME="fedlearnerwins"

function init_para {
    CLUSTER_ID=`aliyun cs DescribeClusters |grep -A 1 name |grep -A 1 $GENERATER_NAME |grep cluster_id |awk -F "\"" '{print $4}'`
}

function delete_vpc {
    echo "Start clearing vpc."

    VPC_ID=`aliyun vpc DescribeVpcs --VpcName $GENERATER_NAME | grep VpcId | awk -F "\"" '{print $4}'`
    if [ -n "$VPC_ID" ]
    then
        echo "Deleting vpc $VPC_ID."
        aliyun vpc DeleteVpc --VpcId $VPC_ID
    fi

    echo "Finish clear vpc."
}

function delete_vswitch {
    echo "Start clearing vswitch."

    VSWITCH_ID=`aliyun vpc DescribeVSwitches --VSwitchName $GENERATER_NAME | grep VSwitchId | awk -F "\"" '{print $4}'`
    if [ -n "$VSWITCH_ID" ]
    then
        echo "Deleting vswitch $VSWITCH_ID."
        aliyun vpc DeleteVSwitch --VSwitchId $VSWITCH_ID
        sleep 5
    fi

    echo "Finish clearing vswitch."
}

function delete_secret {
    echo "Start clearing secret."

    KEYPAIR_NAME=`aliyun ecs DescribeKeyPairs --KeyPairName $GENERATER_NAME | grep KeyPairName | awk -F "\"" '{print $4}'`
    if [ -n "$KEYPAIR_NAME" ]
    then
        echo "Deleting keypair $GENERATER_NAME if it exists."
        aliyun ecs DeleteKeyPairs --KeyPairNames "['$GENERATER_NAME']"
    fi

    echo "Finish clearing secret."
}

function delete_k8s {
    echo "Start clearing k8s cluster."

    CLUSTER_ID=`aliyun cs DescribeClusters |grep -A 1 name |grep -A 1 $GENERATER_NAME |grep cluster_id |awk -F "\"" '{print $4}'`
    if [ -n "$CLUSTER_ID" ]
    then
        echo "Deleting k8s cluster $CLUSTER_ID."
        aliyun cs DeleteCluster --ClusterId $CLUSTER_ID
        STATUS=`aliyun cs DescribeClusters | grep -A 5 name | grep -A 5 $GENERATER_NAME | grep state | awk -F "\"" '{print $4}'`
        while [ -n "$STATUS" ]
        do
            echo "Current k8s cluster status is $STATUS, loop waiting for finish deleting."
            sleep 30
            STATUS=`aliyun cs DescribeClusters | grep -A 5 name | grep -A 5 $GENERATER_NAME | grep state | awk -F "\"" '{print $4}'`
        done
    fi

    echo "Finish clearing k8s cluster."
}

function delete_nas {
    echo "Start clearing nas file system."

    FILE_SYSTEM_ID=`aliyun nas DescribeFileSystems --Description $GENERATER_NAME | grep FileSystemId | awk -F "\"" '{print $4}'`

    if [ -n "$FILE_SYSTEM_ID" ]
    then
        MOUNT_TARGET_DOMAINS=`aliyun nas DescribeMountTargets --FileSystemId $FILE_SYSTEM_ID | grep MountTargetDomain | awk -F "\"" '{print $4}'`
        for mount_target_domain in $MOUNT_TARGET_DOMAINS
        do
            echo "Delete nas file system mount target domain $mount_target_domain."
            aliyun nas DeleteMountTarget --FileSystemId $FILE_SYSTEM_ID --MountTargetDomain $mount_target_domain
            sleep 3
        done

        echo "Deleting nas file system with id $FILE_SYSTEM_ID"
        aliyun nas DeleteFileSystem --FileSystemId $FILE_SYSTEM_ID
        sleep 3
    fi

    echo "Finish clearing nas file system."
}

function delete_db {
    echo "Start clearing database"

    VPC_ID=`aliyun vpc DescribeVpcs --VpcName $GENERATER_NAME | grep VpcId | awk -F "\"" '{print $4}'`
    if [ -n "$VPC_ID" ]
    then
        DBINSTANCE_ID=`aliyun rds DescribeDBInstances --VpcId $VPC_ID | grep \"DBInstanceId\" | awk -F "\"" '{print $4}'`
        if [ -n "$DBINSTANCE_ID" ]
        then
             echo "Delete database instance with id $DBINSTANCE_ID."
             aliyun rds DeleteDBInstance --DBInstanceId $DBINSTANCE_ID
             sleep 5
        fi
    fi

    echo "Finish clearing database"
}


function delete_eip {
    echo "Start clearing public ip address."

    if [ -n "$CLUSTER_ID" ]
    then
        NODES=`aliyun ecs DescribeInstances --InstanceName worker-k8s-for-cs-$CLUSTER_ID | grep InstanceId | awk -F "\"" '{print $4}'`
        for node in $NODES
        do
            ALLOCATION_ID=`aliyun vpc DescribeEipAddresses --AssociatedInstanceId $node --AssociatedInstanceType EcsInstance | grep AllocationId | awk -F "\"" '{print $4}'`
            if [ -n "$ALLOCATION_ID" ]
            then
                echo "Unassociate ip $ALLOCATION_ID with instance $node."
                aliyun vpc UnassociateEipAddress --AllocationId $ALLOCATION_ID --InstanceId $node
                sleep 3

                echo "Release ip $ALLOCATION_ID."
                aliyun vpc ReleaseEipAddress --AllocationId $ALLOCATION_ID
                sleep 3
            fi
        done
    fi

    echo "Finish clearing public ip address."
}

function delete_slb {
    echo "Start clearing slb."

    if [ -z "$CLUSTER_ID" ]
    then
        return
    fi

    LOADBALANCER_ID=`aliyun slb DescribeLoadBalancers --LoadBalancerName ManagedK8SSlbIntranet-$CLUSTER_ID | grep LoadBalancerId | awk -F "\"" '{print $4}'`
    if [ -n "$LOADBALANCER_ID" ]
    then
        echo "Delete the loadbalancer listener 32443, 32443."
        aliyun slb DeleteLoadBalancerListener --ListenerPort 32443 --LoadBalancerId $LOADBALANCER_ID >/dev/null 2>&1
        aliyun slb DeleteLoadBalancerListener --ListenerPort 32400 --LoadBalancerId $LOADBALANCER_ID >/dev/null 2>&1
        sleep 3

        VSERVER_GROUPS=`aliyun slb DescribeVServerGroups --LoadBalancerId $LOADBALANCER_ID | grep VServerGroupId | awk -F "\"" '{print $4}'`
        for vserver_group_id in $VSERVER_GROUPS
        do
            echo "Delete the vserver group with id $vserver_group_id."
            aliyun slb DeleteVServerGroup --VServerGroupId $vserver_group_id
        done
    fi

    echo "Finish clearing slb."
}

function delete_elasticsearch {
    echo "Start clearing elasticsearch."

    ES_INSTANCE_ID=`aliyun elasticsearch ListInstance --description $GENERATER_NAME | grep instanceId | awk -F "\"" '{print $4}' | head -1`

    if [ -n "$ES_INSTANCE_ID" ]
    then
         echo "Delete elasticsearch instance with id $ES_INSTANCE_ID."
         aliyun elasticsearch DeleteInstance --InstanceId $ES_INSTANCE_ID
         sleep 5
    fi

    echo "Finish clearing elasticsearch."
}

init_para
delete_slb
delete_eip
delete_db
delete_nas
delete_elasticsearch
delete_k8s
delete_secret
delete_vswitch
delete_vpc
