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
                name='raw_data_job',
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
                        value='2',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='master_mem',
                        value='3Gi',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_cpu',
                        value='2',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_mem',
                        value='3Gi',
                        access_mode=Variable.PEER_WRITABLE),
                ],
                yaml_template='''{
  "apiVersion": "fedlearner.k8s.io/v1alpha1",
  "kind": "FLApp",
  "metadata": {
    "name": "${workflow.jobs.raw_data_job.name}",
    "namespace": "${project.variables.namespace}"
  },
  "spec": {
    "cleanPodPolicy": "All",
    "flReplicaSpecs": {
      "Master": {
        "pair": false,
        "replicas": 1,
        "template": {
          "spec": {
            "containers": [
              {
                "command": [
                  "/app/deploy/scripts/data_portal/run_data_portal_master.sh"
                ],
                "env": [
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
                  ${project.variables.basic_envs},
                  {
                    "name": "APPLICATION_ID",
                    "value": "${workflow.jobs.raw_data_job.name}"
                  },
                  {
                    "name": "DATA_PORTAL_NAME",
                    "value": "${workflow.jobs.raw_data_job.name}"
                  },
                  {
                    "name": "OUTPUT_PARTITION_NUM",
                    "value": "${workflow.variables.num_partitions}"
                  },
                  {
                    "name": "INPUT_BASE_DIR",
                    "value": "${workflow.jobs.raw_data_job.variables.input_dir}"
                  },
                  {
                    "name": "OUTPUT_BASE_DIR",
                    "value": "${project.variables.storage_root_dir}/raw_data/${workflow.jobs.raw_data_job.name}"
                  },
                  {
                    "name": "RAW_DATA_PUBLISH_DIR",
                    "value": "portal_publish_dir/${workflow.jobs.raw_data_job.name}"
                  },
                  {
                    "name": "DATA_PORTAL_TYPE",
                    "value": "Streaming"
                  },
                  {
                    "name": "FILE_WILDCARD",
                    "value": "${workflow.jobs.raw_data_job.variables.file_wildcard}"
                  }
                ],
                "image": "hub.docker.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                "imagePullPolicy": "IfNotPresent",
                "name": "tensorflow",
                "ports": [
                  {
                    "containerPort": 50051,
                    "name": "flapp-port"
                  }
                ],
                "resources": {
                  "limits": {
                    "cpu": "${workflow.jobs.raw_data_job.variables.master_cpu}",
                    "memory": "${workflow.jobs.raw_data_job.variables.master_mem}"
                  },
                  "requests": {
                    "cpu": "${workflow.jobs.raw_data_job.variables.master_cpu}",
                    "memory": "${workflow.jobs.raw_data_job.variables.master_mem}"
                  }
                },
                "volumeMounts": [
                  {
                    "mountPath": "/data",
                    "name": "data"
                  }
                ]
              }
            ],
            "imagePullSecrets": [
              {
                "name": "regcred"
              }
            ],
            "restartPolicy": "Never",
            "volumes": [
              {
                "name": "data",
                "persistentVolumeClaim": {
                  "claimName": "pvc-fedlearner-default"
                }
              }
            ]
          }
        }
      },
      "Worker": {
        "pair": false,
        "replicas": ${workflow.variables.num_partitions},
        "template": {
          "metadata": {
            "creationTimestamp": null
          },
          "spec": {
            "containers": [
              {
                "command": [
                  "/app/deploy/scripts/data_portal/run_data_portal_worker.sh"
                ],
                "env": [
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
                  ${project.variables.basic_envs},
                  {
                    "name": "CPU_REQUEST",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "requests.cpu"
                      }
                    }
                  },
                  {
                    "name": "MEM_REQUEST",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "requests.memory"
                      }
                    }
                  },
                  {
                    "name": "CPU_LIMIT",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "limits.cpu"
                      }
                    }
                  },
                  {
                    "name": "MEM_LIMIT",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "limits.memory"
                      }
                    }
                  },
                  {
                    "name": "APPLICATION_ID",
                    "value": "${workflow.jobs.raw_data_job.name}"
                  },
                  {
                    "name": "BATCH_SIZE",
                    "value": "${workflow.jobs.raw_data_job.variables.batch_size}"
                  },
                  {
                    "name": "INPUT_DATA_FORMAT",
                    "value": "${workflow.jobs.raw_data_job.variables.input_format}"
                  },
                  {
                    "name": "COMPRESSED_TYPE"
                  },
                  {
                    "name": "OUTPUT_DATA_FORMAT",
                    "value": "${workflow.jobs.raw_data_job.variables.output_format}"
                  }
                ],
                "image": "hub.docker.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                "imagePullPolicy": "IfNotPresent",
                "name": "tensorflow",
                "resources": {
                  "limits": {
                    "cpu": "${workflow.jobs.raw_data_job.variables.worker_cpu}",
                    "memory": "${workflow.jobs.raw_data_job.variables.worker_mem}"
                  },
                  "requests": {
                    "cpu": "${workflow.jobs.raw_data_job.variables.worker_cpu}",
                    "memory": "${workflow.jobs.raw_data_job.variables.worker_mem}"
                  }
                },
                "volumeMounts": [
                  {
                    "mountPath": "/data",
                    "name": "data"
                  }
                ]
              }
            ],
            "imagePullSecrets": [
              {
                "name": "regcred"
              }
            ],
            "restartPolicy": "Never",
            "volumes": [
              {
                "name": "data",
                "persistentVolumeClaim": {
                  "claimName": "pvc-fedlearner-default"
                }
              }
            ]
          }
        }
      }
    },
    "peerSpecs": {
      "Leader": {
        "peerURL": ""
      }
    },
    "role": "Follower"
  }
}
                '''
            ),
            JobDefinition(
                name='data_join_job',
                job_type=JobDefinition.DATA_JOIN,
                is_federated=True,
                is_manual=False,
                variables=[
                    Variable(
                        name='master_cpu',
                        value='2',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='master_mem',
                        value='3Gi',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_cpu',
                        value='2',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='worker_mem',
                        value='3Gi',
                        access_mode=Variable.PEER_WRITABLE),
                    Variable(
                        name='role',
                        value='Follower',
                        access_mode=Variable.PEER_WRITABLE),
                ],
                dependencies=[
                    JobDependency(source='raw_data_job')
                ],
                yaml_template='''
{
  "apiVersion": "fedlearner.k8s.io/v1alpha1",
  "kind": "FLApp",
  "metadata": {
    "name": "${workflow.jobs.data_join_job.name}",
    "namespace": "${project.variables.namespace}"
  },
  "spec": {
    "cleanPodPolicy": "All",
    "flReplicaSpecs": {
      "Master": {
        "pair": true,
        "replicas": 1,
        "template": {
          "metadata": {
            "creationTimestamp": null
          },
          "spec": {
            "containers": [
              {
                "args": [
                  "/app/deploy/scripts/data_join/run_data_join_master.sh"
                ],
                "command": [
                  "/app/deploy/scripts/wait4pair_wrapper.sh"
                ],
                "env": [
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
                  ${project.variables.basic_envs},
                  {
                    "name": "ROLE",
                    "value": "${workflow.jobs.data_join_job.variables.role}"
                  },
                  {
                    "name": "APPLICATION_ID",
                    "value": "${workflow.jobs.data_join_job.name}"
                  },
                  {
                    "name": "OUTPUT_BASE_DIR",
                    "value": "${project.variables.storage_root_dir}/data_source/${workflow.jobs.data_join_job.name}"
                  },
                  {
                    "name": "CPU_REQUEST",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "requests.cpu"
                      }
                    }
                  },
                  {
                    "name": "MEM_REQUEST",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "requests.memory"
                      }
                    }
                  },
                  {
                    "name": "CPU_LIMIT",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "limits.cpu"
                      }
                    }
                  },
                  {
                    "name": "MEM_LIMIT",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "limits.memory"
                      }
                    }
                  },
                  {
                    "name": "BATCH_MODE",
                    "value": "--batch_mode"
                  },
                  {
                    "name": "PARTITION_NUM",
                    "value": "${workflow.jobs.raw_data_job.variables.num_partitions}"
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
                    "value": "portal_publish_dir/${workflow.jobs.data_join_job.name}"
                  },
                  {
                    "name": "RAW_DATA_SUB_DIR",
                    "value": "portal_publish_dir/${workflow.jobs.data_join_job.name}"
                  },
                  {
                    "name": "PARTITION_NUM",
                    "value": "${workflow.jobs.raw_data_job.variables.num_partitions}"
                  }
                ],
                "image": "hub.docker.com/fedlearner/fedlearner:${workflow.variables.image_version}",
                "imagePullPolicy": "IfNotPresent",
                "name": "tensorflow",
                "ports": [
                  {
                    "containerPort": 50051,
                    "name": "flapp-port"
                  }
                ],
                "resources": {
                  "limits": {
                    "cpu": "${workflow.jobs.data_join_job.variables.master_cpu}",
                    "memory": "${workflow.jobs.data_join_job.variables.master_mem}"
                  },
                  "requests": {
                    "cpu": "${workflow.jobs.data_join_job.variables.master_cpu}",
                    "memory": "${workflow.jobs.data_join_job.variables.master_mem}"
                  }
                },
                "volumeMounts": [
                  {
                    "mountPath": "/data",
                    "name": "data"
                  }
                ]
              }
            ],
            "imagePullSecrets": [
              {
                "name": "regcred"
              }
            ],
            "restartPolicy": "Never",
            "volumes": [
              {
                "name": "data",
                "persistentVolumeClaim": {
                  "claimName": "pvc-fedlearner-default"
                }
              }
            ]
          }
        }
      },
      "Worker": {
        "pair": true,
        "replicas": ${workflow.jobs.raw_data_job.variables.num_partitions},
        "template": {
          "metadata": {
            "creationTimestamp": null
          },
          "spec": {
            "containers": [
              {
                "args": [
                  "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                ],
                "command": [
                  "/app/deploy/scripts/wait4pair_wrapper.sh"
                ],
                "env": [
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
                  ${project.variables.basic_envs},
                  {
                    "name": "ROLE",
                    "value": "${workflow.jobs.data_join_job.variables.role}"
                  },
                  {
                    "name": "APPLICATION_ID",
                    "value": "${workflow.jobs.data_join_job.name}"
                  },
                  {
                    "name": "OUTPUT_BASE_DIR",
                    "value": "${project.variables.storage_root_dir}/data_source/${workflow.jobs.data_join_job.name}"
                  },
                  {
                    "name": "CPU_REQUEST",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "requests.cpu"
                      }
                    }
                  },
                  {
                    "name": "MEM_REQUEST",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "requests.memory"
                      }
                    }
                  },
                  {
                    "name": "CPU_LIMIT",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "limits.cpu"
                      }
                    }
                  },
                  {
                    "name": "MEM_LIMIT",
                    "valueFrom": {
                      "resourceFieldRef": {
                        "divisor": "0",
                        "resource": "limits.memory"
                      }
                    }
                  },
                  {
                    "name": "PARTITION_NUM",
                    "value": "${workflow.jobs.raw_data_job.variables.num_partitions}"
                  },
                  {
                    "name": "RAW_DATA_SUB_DIR",
                    "value": "portal_publish_dir/${workflow.jobs.data_join_job.name}"
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
                    "value": "${workflow.jobs.raw_data_job.variables.output_format}"
                  },
                  {
                    "name": "RAW_DATA_SUB_DIR",
                    "value": "portal_publish_dir/${workflow.jobs.raw_data_job.name}"
                  },
                  {
                    "name": "PARTITION_NUM",
                    "value": "${workflow.jobs.raw_data_job.variables.num_partitions}"
                  }
                ],
                "image": "artifact.bytedance.com/fedlearner/fedlearner:5b499dd",
                "imagePullPolicy": "IfNotPresent",
                "name": "tensorflow",
                "ports": [
                  {
                    "containerPort": 50051,
                    "name": "flapp-port"
                  }
                ],
                "resources": {
                  "limits": {
                    "cpu": "${workflow.jobs.data_join_job.variables.master_cpu}",
                    "memory": "${workflow.jobs.data_join_job.variables.master_mem}"
                  },
                  "requests": {
                    "cpu": "${workflow.jobs.data_join_job.variables.master_cpu}",
                    "memory": "${workflow.jobs.data_join_job.variables.master_mem}"
                  }
                },
                "volumeMounts": [
                  {
                    "mountPath": "/data",
                    "name": "data"
                  }
                ]
              }
            ],
            "imagePullSecrets": [
              {
                "name": "regcred"
              }
            ],
            "restartPolicy": "Never",
            "volumes": [
              {
                "name": "data",
                "persistentVolumeClaim": {
                  "claimName": "pvc-fedlearner-default"
                }
              }
            ]
          }
        }
      }
    },
    "peerSpecs": {
      "Follower": {
        "authority": "external.name",
        "extraHeaders": {
          "x-host": "leader.flapp.operator"
        },
        "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
      }
    },
    "role": "Leader"
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
