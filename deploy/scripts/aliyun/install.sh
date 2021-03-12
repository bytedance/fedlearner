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
DB_PASSWORD=$3
ES_PASSWORD=$4
BUCKET=$5
PAY_TYPE=$6

REGION="cn-beijing"
ZONE_ID="cn-beijing-h"
GENERATER_NAME="fedlearnerwins"
VPC_CIDR_BLOCK="192.168.0.0/16"

function echo_exit {
    echo $1
    exit 1
}

function echo_log {
    msg=$1
    echo $msg
    echo $msg >> install.log
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

function create_role {
    ROLE_NAME=$1
    POLICY_NAME=$2
    SERVICE=$3
    aliyun ram CreateRole --RoleName $ROLE_NAME --AssumeRolePolicyDocument "{\"Statement\": [{\"Action\": \"sts:AssumeRole\",\"Effect\": \"Allow\",\"Principal\": {\"Service\": [\"$SERVICE\"]}}],\"Version\": \"1\"}" >/dev/null 2>&1
    aliyun ram AttachPolicyToRole --RoleName $ROLE_NAME --PolicyType System --PolicyName $POLICY_NAME >/dev/null 2>&1
}

function init_policy {
    create_role AliyunNASDefaultRole             AliyunNASRolePolicy                    nas.aliyuncs.com
    create_role AliyunCSClusterRole              AliyunCSClusterRolePolicy              cs.aliyuncs.com
    create_role AliyunCSDefaultRole              AliyunCSDefaultRolePolicy              cs.aliyuncs.com
    create_role AliyunCSKubernetesAuditRole      AliyunCSKubernetesAuditRolePolicy      cs.aliyuncs.com
    create_role AliyunCSManagedArmsRole          AliyunCSManagedArmsRolePolicy          cs.aliyuncs.com
    create_role AliyunCSManagedCmsRole           AliyunCSManagedCmsRolePolicy           cs.aliyuncs.com
    create_role AliyunCSManagedCsiRole           AliyunCSManagedCsiRolePolicy           cs.aliyuncs.com
    create_role AliyunCSManagedKubernetesRole    AliyunCSManagedKubernetesRolePolicy    cs.aliyuncs.com
    create_role AliyunCSManagedLogRole           AliyunCSManagedLogRolePolicy           cs.aliyuncs.com
    create_role AliyunCSManagedNetworkRole       AliyunCSManagedNetworkRolePolicy       cs.aliyuncs.com
    create_role AliyunCSManagedVKRole            AliyunCSManagedVKRolePolicy            cs.aliyuncs.com
    create_role AliyunCSServerlessKubernetesRole AliyunCSServerlessKubernetesRolePolicy cs.aliyuncs.com
    create_role AliyunESSDefaultRole             AliyunESSRolePolicy                    cs.aliyuncs.com

}

function create_oss_bucket {
    aliyun oss mb oss://$BUCKET --storage-class Standard >/dev/null 2>&1
}

function create_vpc {
    VPC_ID=`aliyun vpc DescribeVpcs --VpcName $GENERATER_NAME | grep VpcId | awk -F "\"" '{print $4}'`
    if [[ $VPC_ID == "vpc"* ]]
    then
        echo_log "Vpc $GENERATER_NAME already exists with vpc id $VPC_ID."
    else
        aliyun vpc CreateVpc --CidrBlock $VPC_CIDR_BLOCK --VpcName $GENERATER_NAME
        VPC_ID=`aliyun vpc DescribeVpcs --VpcName $GENERATER_NAME | grep VpcId | awk -F "\"" '{print $4}'`
        if [[ $VPC_ID == "vpc"* ]]
            then
            echo_log "Create vpc $GENERATER_NAME success with vpc id $VPC_ID."
        else
            echo_exit "Failed to create vpc"
        fi

        sleep 5
    fi
}

function create_vswitch {
    VSWITCH_ID=`aliyun vpc DescribeVSwitches --VSwitchName $GENERATER_NAME | grep VSwitchId | awk -F "\"" '{print $4}'`
    if [[ $VSWITCH_ID == "vsw"* ]]
    then
        echo_log "Vswitch $GENERATER_NAME already exists with vswitch id $VSWITCH_ID."
    else
        aliyun vpc CreateVSwitch --VpcId $VPC_ID --CidrBlock $VPC_CIDR_BLOCK --VSwitchName $GENERATER_NAME --ZoneId $ZONE_ID
        VSWITCH_ID=`aliyun vpc DescribeVSwitches --VSwitchName $GENERATER_NAME | grep VSwitchId | awk -F "\"" '{print $4}'`
        if [[ $VSWITCH_ID == "vsw"* ]]
        then
            echo_log "Create vswtich $GENERATER_NAME success with vswtich id $VSWITCH_ID."
        else
            echo_exit "Failed to create vswtich"
        fi

        sleep 5
    fi
}

function create_secret {
    KEYPAIR_NAME=`aliyun ecs DescribeKeyPairs --KeyPairName $GENERATER_NAME | grep KeyPairName | awk -F "\"" '{print $4}'`
    if [ -n "$KEYPAIR_NAME" ]
    then
        echo_log "Keypair $GENERATER_NAME already exists."
    else
        aliyun ecs CreateKeyPair --KeyPairName $GENERATER_NAME
        if [ $? -eq 0 ]
        then
            echo_log "Create keypair $GENERATER_NAME Success."
        else
            echo_exit "Failed to create keypair $GENERATER_NAME."
        fi
    fi
}

function create_k8s_cluster_config {
    rm -rf k8s.json

    echo_log "Generate the kubernetes cluster config file for aliyun."

    if [[ $PAY_TYPE == "postpaid" ]]
    then
        cat <<EOF >>k8s.json
{
    "name": "$GENERATER_NAME",
    "cluster_type": "ManagedKubernetes",
    "disable_rollback": true,
    "timeout_mins": 60,
    "kubernetes_version": "1.16.9-aliyun.1",
    "region_id": "$REGION",
    "snat_entry": true,
    "cloud_monitor_flags": false,
    "endpoint_public_access": true,
    "deletion_protection": false,
    "node_cidr_mask": "26",
    "proxy_mode": "ipvs",
    "tags": [],
    "addons": [
        {
            "name": "flannel"
        },
        {
            "name": "csi-plugin"
        },
        {
            "name": "csi-provisioner"
        },
        {
            "name": "nginx-ingress-controller",
            "disabled": true
        }
    ],
    "os_type": "Linux",
    "platform": "CentOS",
    "runtime": {
        "name": "docker",
        "version": "19.03.5"
    },
    "worker_instance_types": [
        "ecs.c6.3xlarge"
    ],
    "num_of_nodes": 3,
    "worker_system_disk_category": "cloud_efficiency",
    "worker_system_disk_size": 120,
    "worker_instance_charge_type": "PostPaid",
    "vpcid": "$VPC_ID",
    "container_cidr": "172.20.0.0/16",
    "service_cidr": "172.21.0.0/20",
    "vswitch_ids": [
        "$VSWITCH_ID"
    ],
    "key_pair": "$GENERATER_NAME",
    "cpu_policy": "none",
    "is_enterprise_security_group": true
}
EOF
    else
        cat <<EOF >>k8s.json
{
    "name": "$GENERATER_NAME",
    "cluster_type": "ManagedKubernetes",
    "disable_rollback": true,
    "timeout_mins": 60,
    "kubernetes_version": "1.16.9-aliyun.1",
    "region_id": "$REGION",
    "snat_entry": true,
    "cloud_monitor_flags": false,
    "endpoint_public_access": true,
    "deletion_protection": false,
    "node_cidr_mask": "26",
    "proxy_mode": "ipvs",
    "tags": [],
    "addons": [
        {
            "name": "flannel"
        },
        {
            "name": "csi-plugin"
        },
        {
            "name": "csi-provisioner"
        },
        {
            "name": "nginx-ingress-controller",
            "disabled": true
        }
    ],
    "os_type": "Linux",
    "platform": "CentOS",
    "runtime": {
        "name": "docker",
        "version": "19.03.5"
    },
    "worker_instance_types": [
        "ecs.c6.3xlarge"
    ],
    "num_of_nodes": 3,
    "worker_system_disk_category": "cloud_efficiency",
    "worker_system_disk_size": 120,
    "worker_instance_charge_type": "PrePaid",
    "worker_period_unit": "Month",
    "worker_period": 1,
    "worker_auto_renew": true,
    "worker_auto_renew_period": 1,
    "vpcid": "$VPC_ID",
    "container_cidr": "172.20.0.0/16",
    "service_cidr": "172.21.0.0/20",
    "vswitch_ids": [
        "$VSWITCH_ID"
    ],
    "key_pair": "$GENERATER_NAME",
    "cpu_policy": "none",
    "is_enterprise_security_group": true
}
EOF
    fi
}

function create_k8s {
    create_k8s_cluster_config

    CLUSTER_ID=`aliyun cs DescribeClusters | grep -A 1 name | grep -A 1 $GENERATER_NAME | grep cluster_id | awk -F "\"" '{print $4}'`
    if [ -n "$CLUSTER_ID" ]
    then
        echo_log "Kubernetes cluster $GENERATER_NAME already exists with id $CLUSTER_ID."
    else
        CLUSTER_ID=`aliyun cs POST /clusters --header "Content-Type=application/json" --body "$(cat ./k8s.json)" | grep cluster_id | awk -F "\"" '{print $4}'`
        if [ -n "$CLUSTER_ID" ]
        then
            echo_log "Kubernetes cluster $GENERATER_NAME create success with id $CLUSTER_ID."
            STATUS=`aliyun cs DescribeClusters | grep -A 5 name | grep -A 5 $GENERATER_NAME | grep state | awk -F "\"" '{print $4}'`
            while [ "$STATUS" != "running" ]
            do
                echo_log "Current kubernetes cluster status is $STATUS, loop wait until it's running."
                sleep 30
                STATUS=`aliyun cs DescribeClusters | grep -A 5 name | grep -A 5 $GENERATER_NAME | grep state | awk -F "\"" '{print $4}'`
            done
        else
            echo_exit "Failed to create k8s cluster $GENERATER_NAME."
        fi
    fi

    CLUSTER_ID=`aliyun cs DescribeClusters | grep -A 1 name | grep -A 1 $GENERATER_NAME | grep cluster_id | awk -F "\"" '{print $4}'`

    rm -rf tmp config
    echo_log "Creating config file in current dir, you can move it to ~/.kube/config."
    aliyun cs GET /k8s/$CLUSTER_ID/user_config > ./tmp
    json2yaml
    CURRENT_DIR=`pwd`
    export KUBECONFIG="$CURRENT_DIR/config"
    rm -rf tmp k8s.json
}

function create_db {
    DB_INSTANCE_ID=`aliyun rds DescribeDBInstances --VpcId $VPC_ID | grep \"DBInstanceId\" | awk -F "\"" '{print $4}' | head -1`
    if [ -n "$DB_INSTANCE_ID" ]
    then
        echo_log "Database already exists with id $DB_INSTANCE_ID."
    else
        if [[ $PAY_TYPE == "postpaid" ]]
        then
            aliyun rds CreateDBInstance --Engine MySQL --EngineVersion 8.0 --DBInstanceClass rds.mysql.t1.small --DBInstanceStorage 20  --SecurityIPList 0.0.0.0/0 --PayType Postpaid --DBInstanceNetType Intranet --RegionId $REGION --ZoneId $ZONE_ID --VPCId $VPC_ID --InstanceNetworkType VPC
        else
            aliyun rds CreateDBInstance --Engine MySQL --EngineVersion 8.0 --DBInstanceClass rds.mysql.t1.small --DBInstanceStorage 20  --SecurityIPList 0.0.0.0/0 --DBInstanceNetType Intranet --RegionId $REGION --ZoneId $ZONE_ID --VPCId $VPC_ID --InstanceNetworkType VPC --PayType Prepaid --UsedTime 1 --Period Month --AutoRenew true
        fi

        DB_INSTANCE_ID=`aliyun rds DescribeDBInstances --VpcId $VPC_ID | grep \"DBInstanceId\" | awk -F "\"" '{print $4}' | head -1`
        if [ -n "$DB_INSTANCE_ID" ]
        then
            echo_log "Create db instance success with instance id $DB_INSTANCE_ID."
            STATUS=`aliyun rds DescribeDBInstances --VpcId $VPC_ID | grep DBInstanceStatus | awk -F "\"" '{print $4}' | head -1`
            while [ "$STATUS" != "Running" ]
            do
                echo_log "Current db instance status is $STATUS, loop wait until it's running."
                sleep 30
                STATUS=`aliyun rds DescribeDBInstances --VpcId $VPC_ID | grep DBInstanceStatus | awk -F "\"" '{print $4}' | head -1`
            done
        else
            echo_exit "Failed to create db instance."
        fi
    fi

    # Create database account.
    DB_ACCOUNT=`aliyun rds DescribeAccounts --DBInstanceId $DB_INSTANCE_ID | grep fedlearner`
    if [ -z "$DB_ACCOUNT" ]
    then
        aliyun rds CreateAccount --AccountName fedlearner --AccountPassword $DB_PASSWORD --AccountType Super --DBInstanceId $DB_INSTANCE_ID
        if [ $? -eq 0 ]
        then
            echo_log "Create db account fedlearner success."
            sleep 5
        else
            echo_exit "Failed to create db account fedlearner."
        fi
    else
        echo_log "DB account fedlearner already exists."
    fi

    # Create the database.
    DB_FEDLEARNER=`aliyun rds DescribeDatabases --DBInstanceId $DB_INSTANCE_ID | grep fedlearner`
    if [ -z "$DB_ACCOUNT" ]
    then
        aliyun rds CreateDatabase --CharacterSetName utf8mb4 --DBName fedlearner --DBInstanceId $DB_INSTANCE_ID
        if [ $? -eq 0 ]
        then
            echo_log "Create db fedlearner success, waiting 1 minute to update account."
            sleep 60
        else
            echo_exit "Failed to create db fedlearner."
        fi
    else
        echo_log "DB fedlearner already exists."
    fi
}

function create_nas {
    FILE_SYSTEM_ID=`aliyun nas DescribeFileSystems --Description $GENERATER_NAME | grep FileSystemId | awk -F "\"" '{print $4}'`
    if [ -n "$FILE_SYSTEM_ID" ]
    then
        echo_log "Nas file system already exists with id $FILE_SYSTEM_ID."
    else
        FILE_SYSTEM_ID=`aliyun nas CreateFileSystem --ProtocolType NFS --StorageType Capacity --ZoneId $ZONE_ID --Description $GENERATER_NAME | grep FileSystemId | awk -F "\"" '{print $4}'`
        if [ -n "$FILE_SYSTEM_ID" ]
        then
            echo_log "Create nas file system success with id $FILE_SYSTEM_ID."
        else
            echo_exit "Failed to create nas file system."
        fi
    fi

    MOUNT_TARGET_DOMAIN=`aliyun nas DescribeMountTargets --FileSystemId $FILE_SYSTEM_ID | grep MountTargetDomain | awk -F "\"" '{print $4}'`
    if [ -n "$MOUNT_TARGET_DOMAIN" ]
    then
        echo_log "Nas file system $FILE_SYSTEM_ID already has mount target domain $MOUNT_TARGET_DOMAIN"
    else
        aliyun nas CreateMountTarget --AccessGroupName DEFAULT_VPC_GROUP_NAME --NetworkType Vpc --VpcId $VPC_ID --VSwitchId $VSWITCH_ID  --FileSystemId $FILE_SYSTEM_ID
        MOUNT_TARGET_DOMAIN=`aliyun nas DescribeMountTargets --FileSystemId $FILE_SYSTEM_ID | grep MountTargetDomain | awk -F "\"" '{print $4}'`
        if [ -n "$MOUNT_TARGET_DOMAIN" ]
        then
            echo_log "Create nas file system mount target success with domain $MOUNT_TARGET_DOMAIN."
        else
            echo_exit "Failed to create nas file system mount target."
        fi

    fi
}

function list_k8s_nodes {
    NODES=`aliyun ecs DescribeInstances --InstanceName worker-k8s-for-cs-$CLUSTER_ID | grep InstanceId | awk -F "\"" '{print $4}'`
    if [ -n "$NODES" ]
    then
        echo_log "Kubernetes cluster has following nodes:"
        echo_log $NODES
    else
        echo_exit "Failed to list the k8s nodes with name worker-k8s-for-cs-$CLUSTER_ID"
    fi
}

function create_eip {

    EIP_NODE=""
    for node in $NODES
    do
        ALLOCATION_ID=`aliyun vpc DescribeEipAddresses --AssociatedInstanceId $node --AssociatedInstanceType EcsInstance | grep AllocationId | awk -F "\"" '{print $4}'`
        if [ -n "$ALLOCATION_ID" ]
        then
            EIP_NODE=$node
            echo_log "Public ip with id $ALLOCATION_ID has already associate with $EIP_NODE."
            return
        fi
    done

    # Allocate the public ip.
    ALLOCATION_ID=`aliyun vpc AllocateEipAddress --RegionId $REGION --Bandwidth 50 --InstanceChargeType PostPaid --InternetChargeType PayByTraffic --Netmode public | grep AllocationId | awk -F "\"" '{print $4}'`
    if [ -n "$ALLOCATION_ID" ]
    then
        echo_log "Allocate pulbic ip success with id $ALLOCATION_ID."
        sleep 5
    else
        echo_exit "Failed to allocate public ip."
    fi

    # Select the first ecs node to associate with a public ip address.
    for node in $NODES
    do
        EIP_NODE=$node
        break
    done

    # Associate the public ip to the eip node.
    aliyun vpc AssociateEipAddress --AllocationId $ALLOCATION_ID --InstanceId $EIP_NODE
    if [ $? -eq 0 ]
    then
        echo_log "Asscociate public ip $ALLOCATION_ID with instance $EIP_NODE success."
    else
        echo_exit "Failed to asscociate public ip $ALLOCATION_ID with instance $EIP_NODE."
    fi
}

function config_security_group {
    aliyun ecs DescribeSecurityGroups | grep alicloud-cs-auto-created-security-group-$CLUSTER_ID
    if [ $? -ne 0 ]
    then
        echo_exit "Failed to get the wanted security group."
    fi

    SECURITY_GROUP_ID=`aliyun ecs DescribeSecurityGroups --VpcId $VPC_ID | grep -A 5 "ACS Cluster" | grep SecurityGroupId | awk -F "\"" '{print $4}' | head -1`

    echo_log "Config secrity group with id $SECURITY_GROUP_ID"
    aliyun ecs AuthorizeSecurityGroup --RegionId $REGION --SecurityGroupId $SECURITY_GROUP_ID --IpProtocol tcp --PortRange=1/65535 --SourceCidrIp 0.0.0.0/0 --Priority 1
    if [ $? -ne 0 ]
    then
        echo_exit "Failed to config the security group $SECURITY_GROUP_ID."
    fi
}

function config_slb {

    LOADBALANCER_ID=`aliyun slb DescribeLoadBalancers --LoadBalancerName ManagedK8SSlbIntranet-$CLUSTER_ID | grep LoadBalancerId | awk -F "\"" '{print $4}'`
    if [ -z "$LOADBALANCER_ID" ]
    then
        echo_exit "Failed to get the wanted loadbalancers."
    fi

    aliyun slb DescribeVServerGroups --LoadBalancerId $LOADBALANCER_ID --RegionId $REGION | grep http_ingress
    if [ $? -ne 0 ]
    then
        HTTP_INGRESS_VSERVER_GROUP_ID=`aliyun slb CreateVServerGroup --LoadBalancerId $LOADBALANCER_ID --RegionId $REGION --VServerGroupName http_ingress | grep VServerGroupId | awk -F "\"" '{print $4}'`
        echo_log "Create http ingress vserver group success with id $HTTP_INGRESS_VSERVER_GROUP_ID."
        sleep 3

        for node in $NODES
        do
            echo_log "Add backend server $node to vserver group $HTTP_INGRESS_VSERVER_GROUP_ID."
            aliyun slb AddVServerGroupBackendServers --VServerGroupId $HTTP_INGRESS_VSERVER_GROUP_ID --BackendServers "[{\"ServerId\":\"$node\", \"Weight\":\"100\",\"Type\": \"ecs\", \"Port\":\"32080\"}]"
        done
        sleep 3

        echo_log "Create load balancer tpc listener for port 32080 success."
        aliyun slb CreateLoadBalancerTCPListener --ListenerPort 32080 --LoadBalancerId $LOADBALANCER_ID --VServerGroupId $HTTP_INGRESS_VSERVER_GROUP_ID --BackendServerPort 32080 --Bandwidth 50
        sleep 3

        echo_log "Start load balancer listener with port 32080."
        aliyun slb StartLoadBalancerListener --ListenerPort 32080 --LoadBalancerId $LOADBALANCER_ID
        sleep 3

    else
        echo_log "Vserver group http_ingress already exists."
    fi

    aliyun slb DescribeVServerGroups --LoadBalancerId $LOADBALANCER_ID --RegionId $REGION | grep https_ingress
    if [ $? -ne 0 ]
    then
        HTTPS_INGRESS_VSERVER_GROUP_ID=`aliyun slb CreateVServerGroup --LoadBalancerId $LOADBALANCER_ID --RegionId $REGION --VServerGroupName https_ingress | grep VServerGroupId | awk -F "\"" '{print $4}'`
        echo_log "Create https ingress vserver group success with id $HTTPS_INGRESS_VSERVER_GROUP_ID."
        sleep 3

        for node in $NODES
        do
            echo_log "Add backend server $node to vserver group $HTTPS_INGRESS_VSERVER_GROUP_ID."
            aliyun slb AddVServerGroupBackendServers --VServerGroupId $HTTPS_INGRESS_VSERVER_GROUP_ID --BackendServers "[{\"ServerId\":\"$node\", \"Weight\":\"100\",\"Type\": \"ecs\", \"Port\":\"32443\"}]"
        done
        sleep 3

        echo_log "Create load balancer tpc listener for port 32443."
        aliyun slb CreateLoadBalancerTCPListener --ListenerPort 32443 --LoadBalancerId $LOADBALANCER_ID --VServerGroupId $HTTPS_INGRESS_VSERVER_GROUP_ID --BackendServerPort 32443 --Bandwidth 50
        sleep 3

        echo_log "Start load balancer listener with port 32443."
        aliyun slb StartLoadBalancerListener --ListenerPort 32443 --LoadBalancerId $LOADBALANCER_ID
        sleep 3

    else
        echo_log "Vserver group https_ingress already exists."
    fi
}

function create_elasticsearch_config {
    rm -rf es.json

    echo_log "Generate the elasticsearch cluster config file for aliyun."

    if [[ $PAY_TYPE == "postpaid" ]]
    then
        cat <<EOF >>es.json
{
	"description": "$GENERATER_NAME",
	"nodeAmount": 3,
	"paymentType": "postpaid",
	"enablePublic": false,
	"esAdminPassword": "$ES_PASSWORD",
	"nodeSpec": {
		"spec": "elasticsearch.sn1ne.large",
		"disk": 200,
		"diskType": "cloud_ssd",
		"diskEncryption": false
	},
	"networkConfig": {
		"vpcId": "$VPC_ID",
		"vswitchId": "$VSWITCH_ID",
		"vsArea": "$ZONE_ID",
		"type": "vpc"
	},
	"extendConfigs": [
		{
			"configType": "usageScenario",
			"value": "general"
		}
	],
	"esVersion": "7.7_with_X-Pack",
	"haveKibana": true,
	"instanceCategory": "x-pack",
	"kibanaConfiguration": {
		"spec": "elasticsearch.n4.small",
		"amount": 1,
		"disk": 0
	}
}
EOF
    else
        cat <<EOF >>es.json
{
	"description": "$GENERATER_NAME",
	"nodeAmount": 3,
	"paymentType": "prepaid",
	"enablePublic": false,
	"esAdminPassword": "$ES_PASSWORD",
	"nodeSpec": {
		"spec": "elasticsearch.sn1ne.large",
		"disk": 200,
		"diskType": "cloud_ssd",
		"diskEncryption": false
	},
	"networkConfig": {
		"vpcId": "$VPC_ID",
		"vswitchId": "$VSWITCH_ID",
		"vsArea": "$ZONE_ID",
		"type": "vpc"
	},
	"extendConfigs": [
		{
			"configType": "usageScenario",
			"value": "general"
		}
	],
	"esVersion": "7.7_with_X-Pack",
	"haveKibana": true,
	"instanceCategory": "x-pack",
	"kibanaConfiguration": {
		"spec": "elasticsearch.n4.small",
		"amount": 1,
		"disk": 0
	}
}
EOF
    fi
}

function create_filebeat_config {

    rm -rf filebeat.yml
    cat <<EOF >>filebeat.yml
filebeat.config:
  modules:
    path: \${path.config}/modules.d/*.yml
    reload.enabled: false
filebeat.inputs:
- enabled: true
  paths:
  - /var/log/*.log
  - /var/log/messages
  - /var/log/syslog
  type: log
- containers.ids:
  - '*'
  processors:
  - add_kubernetes_metadata:
      in_cluster: true
  - drop_event:
      when:
        equals:
          kubernetes.container.name: filebeat
  type: docker
http.enabled: true
http.port: 5066
output.elasticsearch:
  hosts:
  - http://$ES_INSTANCE_ID.elasticsearch.aliyuncs.com:9200
  username: elastic
  password: $ES_PASSWORD
processors:
- add_cloud_metadata: null
- include_fields:
    fields:
    - host.name
    - input.type
    - kubernetes.container.name
    - kubernetes.namespace
    - kubernetes.node.name
    - kubernetes.pod.name
    - kubernetes.pod.uid
    - log.file.path
    - log.offset
    - message
    - stream
EOF
}


function create_elasticsearch {
    create_elasticsearch_config

    ES_INSTANCE_ID=`aliyun elasticsearch ListInstance --description $GENERATER_NAME | grep instanceId | awk -F "\"" '{print $4}' | head -1`

    if [ -n "$ES_INSTANCE_ID" ]
    then
        echo_log "Elasticsearch instance $GENERATER_NAME already exists with id $ES_INSTANCE_ID."
    else
        ES_INSTANCE_ID=`aliyun elasticsearch createInstance --header "Content-Type=application/json" --body "$(cat ./es.json)" | grep instanceId | awk -F "\"" '{print $4}'`
        if [ -n "$ES_INSTANCE_ID" ]
        then
            echo_log "Elasticsearch instance $GENERATER_NAME create success with id $ES_INSTANCE_ID."
            STATUS=`aliyun elasticsearch DescribeInstance --InstanceId $ES_INSTANCE_ID | grep status | awk -F "\"" '{print $4}' | grep -v NORMAL | head -1`

            while [ "$STATUS" != "active" ]
            do
                echo_log "Current elasticsearch instance status is $STATUS, loop wait until it's active."
                sleep 30
                STATUS=`aliyun elasticsearch DescribeInstance --InstanceId $ES_INSTANCE_ID | grep status | awk -F "\"" '{print $4}' | grep -v NORMAL | head -1`
            done
        else
            echo_exit "Failed to create elasticsearch instance $GENERATER_NAME."
        fi
    fi

    create_filebeat_config
}

function install_fedlearner {

    kubectl get pods | grep fedlearner
    if [ $? -ne 0 ]
    then
        echo_log "Install fedlearner-stack with helm."
        helm install fedlearner-stack ../../charts/fedlearner-stack --set nfs-server-provisioner.enabled=false --set nfs-client-provisioner.enabled=true --set nfs-client-provisioner.nfs.server=$MOUNT_TARGET_DOMAIN --set mariadb.enabled=false
    fi

    #WAITING=`kubectl get pods | grep -E  "ContainerCreating|PodInitializing"`
    #while [ -n "$WAITING" ]
    #do
    #    echo_log "Loop waiting until all the pods are running."
    #    sleep 30
    #    WAITING=`kubectl get pods | grep -E  "ContainerCreating|PodInitializing"`
    #done

    DB_URL=`aliyun rds DescribeDBInstanceNetInfo --DBInstanceId $DB_INSTANCE_ID | grep ConnectionString\" | awk -F "\"" '{print $4}'`
    if [ -n "$DB_URL" ]
    then
        kubectl get pods | grep fedlearner-operator
        if [ $? -ne 0 ]
        then
            echo_log "Install fedlearner operator, apiserver with helm."
            helm install fedlearner ../../charts/fedlearner --set fedlearner-web-console.cluster.env.DB_USERNAME=fedlearner --set fedlearner-web-console.cluster.env.DB_PASSWORD=$DB_PASSWORD --set fedlearner-web-console.cluster.env.DB_HOST=$DB_URL --set fedlearner-web-console.cluster.env.DB_PORT=3306
        fi
    else
        echo_exit "Failed to install fedlearner-operator/api/console since db url not found."
    fi

    rm -rf fedlearner-pvc.yaml
    cat <<EOF >>fedlearner-pvc.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-fedlearner-default
spec:
  accessModes:
  - ReadWriteMany
  capacity:
    storage: 10Gi
  mountOptions:
  - vers=3
  - nolock,tcp,noresvport
  nfs:
    path: /
    server: $MOUNT_TARGET_DOMAIN
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
 name: pvc-fedlearner-default
spec:
 accessModes:
 - ReadWriteMany
 resources:
   requests:
     storage: 10Gi
 volumeName: pv-fedlearner-default
 storageClassName: nfs
EOF

    kubectl apply -f fedlearner-pvc.yaml
    rm -rf fedlearner-pvc.yaml
}

function usage {
    echo "Usage: "
    echo "    ./install.sh access_key_id access_key_secret db_password bucket pay_type"
    echo ""
    echo "Params:"
    echo ""
    echo "    access_key_id:     the access key id provided by aliyun, required"
    echo "    access_key_secret: the access key secret provided by aliyun, required"
    echo "    db_password:       the database password for fedlearner account, required"
    echo "    es_password:       the elasticesearch password for fedlearner account, required"
    echo "    bucket:            the oss bucket to be created, required"
    echo "    pay_type:          the pay_type, default to Prepaid."
}

if [[ -z $ACCESS_KEY_ID ]] || [[ -z $ACCESS_KEY_SECRET ]] || [[ -z $DB_PASSWORD ]] || [[ -z $ES_PASSWORD ]]
then
    usage
    exit 1
else
    install_cli
    init_policy
    create_oss_bucket
    create_vpc
    create_vswitch
    create_secret
    create_db
    create_elasticsearch
    create_nas
    create_k8s
    list_k8s_nodes
    create_eip
    config_security_group
    config_slb
    install_fedlearner
fi
