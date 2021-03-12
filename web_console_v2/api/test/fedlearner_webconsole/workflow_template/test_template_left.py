# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from google.protobuf.json_format import MessageToDict
from fedlearner_webconsole.proto.workflow_definition_pb2 import (
    WorkflowDefinition, JobDefinition, JobDependency
)
from fedlearner_webconsole.proto.common_pb2 import (
    Variable
)


def make_workflow_template():
    workflow = WorkflowDefinition(
        group_alias='test_template',
        is_left=True,
        variables=[
            Variable(
                name='image_version',
                value='v1.5-rc3',
                access_mode=Variable.PEER_READABLE),
            Variable(
                name='num_partitions',
                value='4',
                access_mode=Variable.PEER_WRITABLE),
        ],
        job_definitions=[
            JobDefinition(
                name='raw-data-job',
                job_type=JobDefinition.RAW_DATA,
                is_federated=False,
                is_manual=False,
                variables=[
                    Variable(
                        name='input_dir',
                        value='/app/deploy/integrated_test/tfrecord_raw_data',
                        access_mode=Variable.PRIVATE),
                    Variable(
                        name='file_wildcard',
                        value='*.rd',
                        access_mode=Variable.PRIVATE),
                    Variable(
                        name='batch_size',
                        value='1024',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='input_format',
                        value='TF_RECORD',
                        access_mode=Variable.PRIVATE),
                    Variable(
                        name='output_format',
                        value='TF_RECORD',
                        access_mode=Variable.PRIVATE),
                    Variable(
                        name='master_cpu',
                        value='2000m',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='master_mem',
                        value='3Gi',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_cpu',
                        value='2000m',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_mem',
                        value='4Gi',
                        access_mode=Variable.PEER_WRITABLE),
                ],
                yaml_template='''{
    "apiVersion": "fedlearner.k8s.io/v1alpha1",
    "kind": "FLApp",
    "metadata": {
        "name": "${workflow.jobs.raw-data-job.name}",
        "namespace": "${project.variables.namespace}"
    },
    "spec": {
        "role": "Follower",
        "peerSpecs": {
            "Leader": {
                "peerURL": "",
                "authority": ""
            }
        },
        "cleanPodPolicy": "All",
        "flReplicaSpecs": {
            "Master": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "resources": {
                                    "limits": {
                                        "cpu": "${workflow.jobs.raw-data-job.variables.master_cpu}",
                                        "memory": "${workflow.jobs.raw-data-job.variables.master_mem}"
                                    },
                                    "requests": {
                                        "cpu": "${workflow.jobs.raw-data-job.variables.master_cpu}",
                                        "memory": "${workflow.jobs.raw-data-job.variables.master_mem}"
                                    }
                                },
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "flapp-port"
                                    }
                                ],
                                "command": [
                                    "/app/deploy/scripts/data_portal/run_data_portal_master.sh"
                                ],
                                "args": [],
                                "env": [
                                    ${system.basic_envs},
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value": "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "DATA_PORTAL_NAME",
                                        "value": "${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "OUTPUT_PARTITION_NUM",
                                        "value": "${workflow.variables.num_partitions}"
                                    },
                                    {
                                        "name": "INPUT_BASE_DIR",
                                        "value": "${workflow.jobs.raw-data-job.variables.input_dir}"
                                    },
                                    {
                                        "name": "OUTPUT_BASE_DIR",
                                        "value": "${project.variables.storage_root_dir}/raw_data/${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "RAW_DATA_PUBLISH_DIR",
                                        "value": "portal_publish_dir/${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "DATA_PORTAL_TYPE",
                                        "value": "Streaming"
                                    },
                                    {
                                        "name": "FILE_WILDCARD",
                                        "value": "${workflow.jobs.raw-data-job.variables.file_wildcard}"
                                    }
                                ],
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow"
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ],
                        "restartPolicy": "Never"
                    }
                },
                "pair": false,
                "replicas": 1
            },
            "Worker": {
                "replicas": 4,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "resources": {
                                    "limits": {
                                        "cpu": "${workflow.jobs.raw-data-job.variables.worker_cpu}",
                                        "memory": "${workflow.jobs.raw-data-job.variables.worker_mem}"
                                    },
                                    "requests": {
                                        "cpu": "${workflow.jobs.raw-data-job.variables.worker_cpu}",
                                        "memory": "${workflow.jobs.raw-data-job.variables.worker_mem}"
                                    }
                                },
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "command": [
                                    "/app/deploy/scripts/data_portal/run_data_portal_worker.sh"
                                ],
                                "args": [],
                                "env": [
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value": "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    ${system.basic_envs},
                                    {
                                        "name": "CPU_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "CPU_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "BATCH_SIZE",
                                        "value": "${workflow.jobs.raw-data-job.variables.batch_size}"
                                    },
                                    {
                                        "name": "INPUT_DATA_FORMAT",
                                        "value": "${workflow.jobs.raw-data-job.variables.input_format}"
                                    },
                                    {
                                        "name": "COMPRESSED_TYPE",
                                        "value": ""
                                    },
                                    {
                                        "name": "OUTPUT_DATA_FORMAT",
                                        "value": "${workflow.jobs.raw-data-job.variables.output_format}"
                                    }
                                ],
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow"
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ],
                        "restartPolicy": "Never"
                    }
                },
                "pair": false
            }
        }
    }
}
                '''
            ),
            JobDefinition(
                name='data-join-job',
                job_type=JobDefinition.DATA_JOIN,
                is_federated=True,
                is_manual=False,
                variables=[
                    Variable(
                        name='master_cpu',
                        value='2000m',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='master_mem',
                        value='3Gi',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_cpu',
                        value='4000m',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_mem',
                        value='4Gi',
                        access_mode=Variable.PEER_WRITABLE),
                ],
                dependencies=[
                    JobDependency(source='raw-data-job')
                ],
                yaml_template='''
{
    "apiVersion": "fedlearner.k8s.io/v1alpha1",
    "kind": "FLApp",
    "metadata": {
        "name": "${workflow.jobs.data-join-job.name}",
        "namespace": "${project.variables.namespace}"
    },
    "spec": {
        "role": "Leader",
        "cleanPodPolicy": "All",
        "peerSpecs": {
            "Follower": {
                "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
                "authority": "${project.participants[0].egress_domain}",
                "extraHeaders": {
                    "x-host": "default.fedlearner.operator"
                }
            }
        },
        "flReplicaSpecs": {
            "Master": {
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "env": [
                                    ${system.basic_envs},
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value": "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ROLE",
                                        "value": "leader"
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    },
                                    {
                                        "name": "OUTPUT_BASE_DIR",
                                        "value": "${project.variables.storage_root_dir}/data_source/${workflow.jobs.data-join-job.name}"
                                    },
                                    {
                                        "name": "CPU_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "CPU_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "BATCH_MODE",
                                        "value": "--batch_mode"
                                    },
                                    {
                                        "name": "PARTITION_NUM",
                                        "value": "${workflow.variables.num_partitions}"
                                    },
                                    {
                                        "name": "START_TIME",
                                        "value": "0"
                                    },
                                    {
                                        "name": "END_TIME",
                                        "value": "999999999999"
                                    },
                                    {
                                        "name": "NEGATIVE_SAMPLING_RATE",
                                        "value": "1.0"
                                    },
                                    {
                                        "name": "RAW_DATA_SUB_DIR",
                                        "value": "portal_publish_dir/${workflow.jobs.raw-data-job.name}"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow",
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "flapp-port"
                                    }
                                ],
                                "command": [
                                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                                ],
                                "args": [
                                    "/app/deploy/scripts/data_join/run_data_join_master.sh"
                                ],
                                "resources": {
                                      "limits": {
                                        "cpu": "${workflow.jobs.data-join-job.variables.master_cpu}",
                                        "memory": "${workflow.jobs.data-join-job.variables.master_mem}"
                                      },
                                      "requests": {
                                        "cpu": "${workflow.jobs.data-join-job.variables.master_cpu}",
                                        "memory": "${workflow.jobs.data-join-job.variables.master_mem}"
                                      }
                                }
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ]
                    }
                },
                "pair": true,
                "replicas": 1
            },
            "Worker": {
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "env": [
                                    ${system.basic_envs},
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value": "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ROLE",
                                        "value": "leader"
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    },
                                    {
                                        "name": "OUTPUT_BASE_DIR",
                                        "value": "${project.variables.storage_root_dir}/data_source/${workflow.jobs.data-join-job.name}"
                                    },
                                    {
                                        "name": "CPU_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "CPU_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "PARTITION_NUM",
                                        "value": "${workflow.variables.num_partitions}"
                                    },
                                    {
                                        "name": "RAW_DATA_SUB_DIR",
                                        "value": "portal_publish_dir/${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "DATA_BLOCK_DUMP_INTERVAL",
                                        "value": "600"
                                    },
                                    {
                                        "name": "DATA_BLOCK_DUMP_THRESHOLD",
                                        "value": "65536"
                                    },
                                    {
                                        "name": "EXAMPLE_ID_DUMP_INTERVAL",
                                        "value": "600"
                                    },
                                    {
                                        "name": "EXAMPLE_ID_DUMP_THRESHOLD",
                                        "value": "65536"
                                    },
                                    {
                                        "name": "EXAMPLE_ID_BATCH_SIZE",
                                        "value": "4096"
                                    },
                                    {
                                        "name": "MAX_FLYING_EXAMPLE_ID",
                                        "value": "307152"
                                    },
                                    {
                                        "name": "MIN_MATCHING_WINDOW",
                                        "value": "2048"
                                    },
                                    {
                                        "name": "MAX_MATCHING_WINDOW",
                                        "value": "8192"
                                    },
                                    {
                                        "name": "RAW_DATA_ITER",
                                        "value": "${workflow.jobs.raw-data-job.variables.output_format}"
                                    },
                                    {
                                        "name": "RAW_DATA_SUB_DIR",
                                        "value": "portal_publish_dir/${workflow.jobs.raw-data-job.name}"
                                    },
                                    {
                                        "name": "PARTITION_NUM",
                                        "value": "${workflow.variables.num_partitions}"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow",
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "flapp-port"
                                    }
                                ],
                                "command": [
                                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                                ],
                                "args": [
                                    "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                                ],
                                "resources": {
                                    "limits": {
                                        "cpu": "${workflow.jobs.data-join-job.variables.worker_cpu}",
                                        "memory": "${workflow.jobs.data-join-job.variables.worker_mem}"
                                    },
                                    "requests": {
                                        "cpu": "${workflow.jobs.data-join-job.variables.worker_cpu}",
                                        "memory": "${workflow.jobs.data-join-job.variables.worker_mem}"
                                    }
                                }
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ]
                    }
                },
                "pair": true,
                "replicas": ${workflow.variables.num_partitions}
            }
        }
    }
}
                '''
            ),
            JobDefinition(
                name='train-job',
                job_type=JobDefinition.NN_MODEL_TRANINING,
                is_federated=True,
                is_manual=False,
                variables=[
                    Variable(
                        name='code_key',
                        value='/app/deploy/integrated_test/code_key/criteo-train-2.tar.gz',
                        access_mode=Variable.PRIVATE
                    )
                ],
                dependencies=[
                    JobDependency(source='data-join-job')
                ],
                yaml_template='''
                {
    "apiVersion": "fedlearner.k8s.io/v1alpha1",
    "kind": "FLApp",
    "metadata": {
        "name": "${workflow.jobs.train-job.name}",
        "namespace": "${project.variables.namespace}"
    },
    "spec": {
        "role": "Follower",
        "cleanPodPolicy": "All",
        "peerSpecs": {
            "Leader": {
                "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
                "authority": "${project.participants[0].egress_domain}",
                "extraHeaders": {
                    "x-host": "default.fedlearner.operator"
                }
            }
        },
        "flReplicaSpecs": {
            "Master": {
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "env": [
                                    ${system.basic_envs},
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value":  "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ROLE",
                                        "value": "follower"
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.train-job.name}"
                                    },
                                    {
                                        "name": "OUTPUT_BASE_DIR",
                                        "value": "${project.variables.storage_root_dir}/job_output/${workflow.jobs.train-job.name}"
                                    },
                                    {
                                        "name": "CPU_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "CPU_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "DATA_SOURCE",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow",
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "flapp-port"
                                    }
                                ],
                                "command": [
                                    "/app/deploy/scripts/trainer/run_trainer_master.sh"
                                ],
                                "args": [],
                                "resources": {
                                      "limits": {
                                        "cpu": "2000m",
                                        "memory": "2Gi"
                                      },
                                      "requests": {
                                        "cpu": "1000m",
                                        "memory": "2Gi"
                                      }
                                }
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ]
                    }
                },
                "replicas": 1,
                "pair": false
            },
            "PS": {
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "env": [
                                    ${system.basic_envs},
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value": "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ROLE",
                                        "value": "follower"
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.train-job.name}"
                                    },
                                    {
                                        "name": "OUTPUT_BASE_DIR",
                                        "value": "${project.variables.storage_root_dir}/job_output/${workflow.jobs.train-job.name}"
                                    },
                                    {
                                        "name": "CPU_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "CPU_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "DATA_SOURCE",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    },
                                    {
                                        "name": "DATA_SOURCE",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow",
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "flapp-port"
                                    }
                                ],
                                "command": [
                                    "/app/deploy/scripts/trainer/run_trainer_ps.sh"
                                ],
                                "args": [],
                                "resources": {
                                    "limits": {
                                        "cpu": "2000m",
                                        "memory": "4Gi"
                                    },
                                    "requests": {
                                        "cpu": "1000m",
                                        "memory": "2Gi"
                                    }
                                }
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ]
                    }
                },
                "pair": false,
                "replicas": 1
            },
            "Worker": {
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "env": [
                                    ${system.basic_envs},
                                    {
                                        "name": "STORAGE_ROOT_PATH",
                                        "value": "${project.variables.storage_root_dir}"
                                    },
                                    {
                                        "name": "POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        }
                                    },
                                    {
                                        "name": "POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.name"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ROLE",
                                        "value": "follower"
                                    },
                                    {
                                        "name": "APPLICATION_ID",
                                        "value": "${workflow.jobs.train-job.name}"
                                    },
                                    {
                                        "name": "OUTPUT_BASE_DIR",
                                        "value": "${project.variables.storage_root_dir}/job_output/${workflow.jobs.train-job.name}"
                                    },
                                    {
                                        "name": "CPU_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_REQUEST",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "requests.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "CPU_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.cpu"
                                            }
                                        }
                                    },
                                    {
                                        "name": "MEM_LIMIT",
                                        "valueFrom": {
                                            "resourceFieldRef": {
                                                "resource": "limits.memory"
                                            }
                                        }
                                    },
                                    {
                                        "name": "ETCD_NAME",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "ETCD_ADDR",
                                        "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
                                    },
                                    {
                                        "name": "ETCD_BASE_DIR",
                                        "value": "fedlearner"
                                    },
                                    {
                                        "name": "EGRESS_URL",
                                        "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
                                    },
                                    {
                                        "name": "EGRESS_HOST",
                                        "value": "${project.participants[0].egress_host}"
                                    },
                                    {
                                        "name": "EGRESS_DOMAIN",
                                        "value": "${project.participants[0].egress_domain}"
                                    },
                                    {
                                        "name": "CODE_KEY",
                                        "value": "${workflow.jobs.train-job.variables.code_key}"
                                    },
                                    {
                                        "name": "SAVE_CHECKPOINT_STEPS",
                                        "value": "1000"
                                    },
                                    {
                                        "name": "DATA_SOURCE",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    },
                                    {
                                        "name": "DATA_SOURCE",
                                        "value": "${workflow.jobs.data-join-job.name}"
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "name": "tensorflow",
                                "volumeMounts": [
                                    {
                                        "mountPath": "/data",
                                        "name": "data"
                                    }
                                ],
                                "image": "artifact.bytedance.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "flapp-port"
                                    },
                                    {
                                        "containerPort": 50052,
                                        "name": "tf-port"
                                    }
                                ],
                                "command": [
                                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                                ],
                                "args": [
                                    "/app/deploy/scripts/trainer/run_trainer_worker.sh"
                                ],
                                "resources": {
                                    "limits": {
                                        "cpu": "2000m",
                                        "memory": "4Gi"
                                    },
                                    "requests": {
                                        "cpu": "1000m",
                                        "memory": "2Gi"
                                    }
                                }
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": [
                            {
                                "persistentVolumeClaim": {
                                    "claimName": "pvc-fedlearner-default"
                                },
                                "name": "data"
                            }
                        ]
                    }
                },
                "pair": true,
                "replicas": ${workflow.variables.num_partitions}
            }
        }
    }
}
                '''
            )
        ])

    return workflow


import json

if __name__ == '__main__':
    print(json.dumps(MessageToDict(
        make_workflow_template(),
        preserving_proto_field_name=True,
        including_default_value_fields=True)))
