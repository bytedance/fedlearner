export const mockJobList = {
    "data": [
      {
        "kind": "FLApp",
        "apiVersion": "fedlearner.k8s.io/v1alpha1",
        "metadata": {
          "name": "fl-360-join-job-v1",
          "namespace": "leader",
          "selfLink": "/apis/fedlearner.k8s.io/v1alpha1/namespaces/leader/flapps/fl-360-join-job-v1",
          "uid": "fe325625-f3fb-11ea-8a95-b8599fc6257e",
          "resourceVersion": "203056955",
          "generation": 1,
          "creationTimestamp": "2020-09-11T06:57:01Z"
        },
        "spec": {
          "cleanPodPolicy": "All",
          "flReplicaSpecs": {
            "Master": {
              "replicas": 1,
              "pair": true,
              "template": {
                "metadata": {
                  "creationTimestamp": null
                },
                "spec": {
                  "volumes": [
                    {
                      "name": "pyutil",
                      "hostPath": {
                        "path": "/opt/tiger/pyutil"
                      }
                    },
                    {
                      "name": "yarn-deploy",
                      "hostPath": {
                        "path": "/opt/tiger/yarn_deploy"
                      }
                    },
                    {
                      "name": "jdk",
                      "hostPath": {
                        "path": "/opt/tiger/jdk"
                      }
                    }
                  ],
                  "containers": [
                    {
                      "name": "tensorflow",
                      "image": "artifact.bytedance.com/fedlearner/fedlearner:d251463",
                      "command": [
                        "/app/deploy/scripts/wait4pair_wrapper.sh"
                      ],
                      "args": [
                        "/app/deploy/scripts/data_join/run_data_join_master.sh"
                      ],
                      "ports": [
                        {
                          "name": "flapp-port",
                          "containerPort": 50051
                        }
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
                        {
                          "name": "ROLE",
                          "value": "follower"
                        },
                        {
                          "name": "APPLICATION_ID",
                          "value": "fl-360-join-job-v1"
                        },
                        {
                          "name": "OUTPUT_BASE_DIR",
                          "value": "hdfs:///home/byte_ad_va/data/fl/360_jie_tiao/user_profile_201912/data_source/fl-360-join-job-v1"
                        },
                        {
                          "name": "CPU_REQUEST",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "requests.cpu",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "MEM_REQUEST",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "requests.memory",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "CPU_LIMIT",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "limits.cpu",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "MEM_LIMIT",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "limits.memory",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "ES_HOST",
                          "value": "fedlearner-es.byted.org"
                        },
                        {
                          "name": "ES_PORT",
                          "value": "80"
                        },
                        {
                          "name": "SEC_TOKEN_PATH",
                          "value": "/etc/token/identity-token"
                        },
                        {
                          "name": "ETCD_NAME",
                          "value": "fedlearner"
                        },
                        {
                          "name": "ETCD_ADDR",
                          "value": "10.10.73.87:2379"
                        },
                        {
                          "name": "ETCD_BASE_DIR",
                          "value": "jinrong360"
                        },
                        {
                          "name": "EGRESS_URL",
                          "value": "ingress-nginx.ingress-nginx.svc.cluster.local:80"
                        },
                        {
                          "name": "EGRESS_HOST",
                          "value": "fl-360jinrong-client-auth.com"
                        },
                        {
                          "name": "EGRESS_DOMAIN",
                          "value": "fl-360jinrong.com"
                        },
                        {
                          "name": "TCE_PSM",
                          "value": "data.aml.fl"
                        },
                        {
                          "name": "TCE_PSM_GROUP",
                          "value": "default"
                        },
                        {
                          "name": "TCE_PSM_OWNER",
                          "value": "lilongyijia"
                        },
                        {
                          "name": "TCE_CLUSTER",
                          "value": "default"
                        },
                        {
                          "name": "HADOOP_HOME",
                          "value": "/opt/tiger/yarn_deploy/hadoop"
                        },
                        {
                          "name": "JAVA_HOME",
                          "value": "/opt/tiger/jdk/jdk1.8"
                        },
                        {
                          "name": "RUNTIME_IDC_NAME",
                          "value": "lf"
                        },
                        {
                          "name": "BATCH_MODE",
                          "value": "--batch_mode"
                        },
                        {
                          "name": "PARTITION_NUM",
                          "value": "4"
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
                          "value": "portal_publish_dir/fl-360-csv-data-v4"
                        }
                      ],
                      "resources": {
                        "limits": {
                          "cpu": "2",
                          "memory": "3Gi"
                        },
                        "requests": {
                          "cpu": "2",
                          "memory": "3Gi"
                        }
                      },
                      "volumeMounts": [
                        {
                          "name": "pyutil",
                          "mountPath": "/opt/tiger/pyutil"
                        },
                        {
                          "name": "yarn-deploy",
                          "mountPath": "/opt/tiger/yarn_deploy"
                        },
                        {
                          "name": "jdk",
                          "mountPath": "/opt/tiger/jdk"
                        }
                      ],
                      "imagePullPolicy": "IfNotPresent"
                    }
                  ],
                  "restartPolicy": "Never",
                  "imagePullSecrets": [
                    {
                      "name": "regcred-bd"
                    }
                  ]
                }
              }
            },
            "Worker": {
              "replicas": 4,
              "pair": true,
              "template": {
                "metadata": {
                  "creationTimestamp": null
                },
                "spec": {
                  "volumes": [
                    {
                      "name": "pyutil",
                      "hostPath": {
                        "path": "/opt/tiger/pyutil"
                      }
                    },
                    {
                      "name": "yarn-deploy",
                      "hostPath": {
                        "path": "/opt/tiger/yarn_deploy"
                      }
                    },
                    {
                      "name": "jdk",
                      "hostPath": {
                        "path": "/opt/tiger/jdk"
                      }
                    }
                  ],
                  "containers": [
                    {
                      "name": "tensorflow",
                      "image": "artifact.bytedance.com/fedlearner/fedlearner:d251463",
                      "command": [
                        "/app/deploy/scripts/wait4pair_wrapper.sh"
                      ],
                      "args": [
                        "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                      ],
                      "ports": [
                        {
                          "name": "flapp-port",
                          "containerPort": 50051
                        }
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
                        {
                          "name": "ROLE",
                          "value": "follower"
                        },
                        {
                          "name": "APPLICATION_ID",
                          "value": "fl-360-join-job-v1"
                        },
                        {
                          "name": "OUTPUT_BASE_DIR",
                          "value": "hdfs:///home/byte_ad_va/data/fl/360_jie_tiao/user_profile_201912/data_source/fl-360-join-job-v1"
                        },
                        {
                          "name": "CPU_REQUEST",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "requests.cpu",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "MEM_REQUEST",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "requests.memory",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "CPU_LIMIT",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "limits.cpu",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "MEM_LIMIT",
                          "valueFrom": {
                            "resourceFieldRef": {
                              "resource": "limits.memory",
                              "divisor": "0"
                            }
                          }
                        },
                        {
                          "name": "ES_HOST",
                          "value": "fedlearner-es.byted.org"
                        },
                        {
                          "name": "ES_PORT",
                          "value": "80"
                        },
                        {
                          "name": "SEC_TOKEN_PATH",
                          "value": "/etc/token/identity-token"
                        },
                        {
                          "name": "ETCD_NAME",
                          "value": "fedlearner"
                        },
                        {
                          "name": "ETCD_ADDR",
                          "value": "10.10.73.87:2379"
                        },
                        {
                          "name": "ETCD_BASE_DIR",
                          "value": "jinrong360"
                        },
                        {
                          "name": "EGRESS_URL",
                          "value": "ingress-nginx.ingress-nginx.svc.cluster.local:80"
                        },
                        {
                          "name": "EGRESS_HOST",
                          "value": "fl-360jinrong-client-auth.com"
                        },
                        {
                          "name": "EGRESS_DOMAIN",
                          "value": "fl-360jinrong.com"
                        },
                        {
                          "name": "TCE_PSM",
                          "value": "data.aml.fl"
                        },
                        {
                          "name": "TCE_PSM_GROUP",
                          "value": "default"
                        },
                        {
                          "name": "TCE_PSM_OWNER",
                          "value": "lilongyijia"
                        },
                        {
                          "name": "TCE_CLUSTER",
                          "value": "default"
                        },
                        {
                          "name": "HADOOP_HOME",
                          "value": "/opt/tiger/yarn_deploy/hadoop"
                        },
                        {
                          "name": "JAVA_HOME",
                          "value": "/opt/tiger/jdk/jdk1.8"
                        },
                        {
                          "name": "RUNTIME_IDC_NAME",
                          "value": "lf"
                        },
                        {
                          "name": "DATA_BLOCK_DUMP_INTERVAL",
                          "value": "300"
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
                          "value": "262144"
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
                          "value": "256"
                        },
                        {
                          "name": "MAX_MATCHING_WINDOW",
                          "value": "1024"
                        },
                        {
                          "name": "RAW_DATA_ITER",
                          "value": "CSV_DICT"
                        },
                        {
                          "name": "MIN_MATCHING_WINDOW",
                          "value": "128"
                        },
                        {
                          "name": "MAX_MATCHING_WINDOW",
                          "value": "1024"
                        },
                        {
                          "name": "DATA_BLOCK_DUMP_INTERVAL",
                          "value": "300"
                        },
                        {
                          "name": "DATA_BLOCK_DUMP_THRESHOLD",
                          "value": "202144"
                        },
                        {
                          "name": "EXAMPLE_ID_DUMP_INTERVAL",
                          "value": "600"
                        },
                        {
                          "name": "EXAMPLE_ID_DUMP_THRESHOLD",
                          "value": "262144"
                        },
                        {
                          "name": "EXAMPLE_ID_BATCH_SIZE",
                          "value": "4096"
                        },
                        {
                          "name": "MAX_FLYING_EXAMPLE_ID",
                          "value": "307152"
                        }
                      ],
                      "resources": {
                        "limits": {
                          "cpu": "18",
                          "memory": "12Gi"
                        },
                        "requests": {
                          "cpu": "18",
                          "memory": "12Gi"
                        }
                      },
                      "volumeMounts": [
                        {
                          "name": "pyutil",
                          "mountPath": "/opt/tiger/pyutil"
                        },
                        {
                          "name": "yarn-deploy",
                          "mountPath": "/opt/tiger/yarn_deploy"
                        },
                        {
                          "name": "jdk",
                          "mountPath": "/opt/tiger/jdk"
                        }
                      ],
                      "imagePullPolicy": "IfNotPresent"
                    }
                  ],
                  "restartPolicy": "Never",
                  "imagePullSecrets": [
                    {
                      "name": "regcred-bd"
                    }
                  ]
                }
              }
            }
          },
          "role": "Follower",
          "peerSpecs": {
            "Leader": {
              "peerURL": "ingress-nginx.ingress-nginx.svc.cluster.local:80",
              "authority": "fl-360jinrong.com",
              "extraHeaders": {
                "x-host": "default.fedlearner.operator"
              }
            }
          }
        },
        "status": {
          "appState": "FLStateComplete",
          "flReplicaStatus": {
            "Master": {
              "local": {
                "fl-360-join-job-v1-follower-master-0": {}
              },
              "remote": {
                "fl-360-join-job-v1-leader-master-0": {}
              },
              "mapping": {
                "fl-360-join-job-v1-follower-master-0": "fl-360-join-job-v1-leader-master-0"
              },
              "active": {},
              "succeeded": {
                "fl-360-join-job-v1-follower-master-0-f325ef64-6c7b-4fc4-b889-c56caf8e882d": {}
              },
              "failed": {}
            },
            "Worker": {
              "local": {
                "fl-360-join-job-v1-follower-worker-0": {},
                "fl-360-join-job-v1-follower-worker-1": {},
                "fl-360-join-job-v1-follower-worker-2": {},
                "fl-360-join-job-v1-follower-worker-3": {}
              },
              "remote": {
                "fl-360-join-job-v1-leader-worker-0": {},
                "fl-360-join-job-v1-leader-worker-1": {},
                "fl-360-join-job-v1-leader-worker-2": {},
                "fl-360-join-job-v1-leader-worker-3": {}
              },
              "mapping": {
                "fl-360-join-job-v1-follower-worker-0": "fl-360-join-job-v1-leader-worker-0",
                "fl-360-join-job-v1-follower-worker-1": "fl-360-join-job-v1-leader-worker-1",
                "fl-360-join-job-v1-follower-worker-2": "fl-360-join-job-v1-leader-worker-2",
                "fl-360-join-job-v1-follower-worker-3": "fl-360-join-job-v1-leader-worker-3"
              },
              "active": {},
              "succeeded": {
                "fl-360-join-job-v1-follower-worker-0-448152c9-5aae-402b-ad77-e36118ac079b": {},
                "fl-360-join-job-v1-follower-worker-1-ade540d3-d3ce-4aef-8a73-cb7361f7b43a": {},
                "fl-360-join-job-v1-follower-worker-2-9964ecf7-0db1-4888-9565-a95424c345ea": {},
                "fl-360-join-job-v1-follower-worker-3-68485ee7-6120-465d-ab42-4578b78d4f6b": {}
              },
              "failed": {}
            }
          }
        },
        "localdata": {
          "server_params": {
            "spec": {
              "flReplicaSpecs": {
                "Master": {
                  "replicas": 1,
                  "template": {
                    "spec": {
                      "containers": [
                        {
                          "resources": {
                            "limits": {
                              "cpu": "2000m",
                              "memory": "3Gi"
                            },
                            "requests": {
                              "cpu": "2000m",
                              "memory": "3Gi"
                            }
                          }
                        }
                      ]
                    }
                  }
                },
                "Worker": {
                  "replicas": 4,
                  "template": {
                    "spec": {
                      "containers": [
                        {
                          "env": [
                            {
                              "name": "test flag",
                              "value": "test "
                            },
                            {
                              "name": "MIN_MATCHING_WINDOW",
                              "value": "128"
                            },
                            {
                              "name": "MAX_MATCHING_WINDOW",
                              "value": "1024"
                            },
                            {
                              "name": "DATA_BLOCK_DUMP_INTERVAL",
                              "value": "300"
                            },
                            {
                              "name": "DATA_BLOCK_DUMP_THRESHOLD",
                              "value": "262144"
                            },
                            {
                              "name": "EXAMPLE_ID_DUMP_INTERVAL",
                              "value": "600"
                            },
                            {
                              "name": "EXAMPLE_ID_DUMP_THRESHOLD",
                              "value": "262144"
                            },
                            {
                              "name": "EXAMPLE_ID_BATCH_SIZE",
                              "value": "4096"
                            },
                            {
                              "name": "MAX_FLYING_EXAMPLE_ID",
                              "value": "307152"
                            }
                          ],
                          "resources": {
                            "limits": {
                              "cpu": "3000m",
                              "memory": "6Gi"
                            },
                            "requests": {
                              "cpu": "3000m",
                              "memory": "6Gi"
                            }
                          }
                        }
                      ]
                    }
                  }
                }
              }
            }
          },
          "client_params": {
            "spec": {
              "flReplicaSpecs": {
                "Master": {
                  "replicas": 1,
                  "template": {
                    "spec": {
                      "containers": [
                        {
                          "resources": {
                            "limits": {
                              "cpu": "2000m",
                              "memory": "3Gi"
                            },
                            "requests": {
                              "cpu": "2000m",
                              "memory": "3Gi"
                            }
                          }
                        }
                      ]
                    }
                  }
                },
                "Worker": {
                  "replicas": 4,
                  "template": {
                    "spec": {
                      "containers": [
                        {
                          "env": [
                            {
                              "name": "MIN_MATCHING_WINDOW",
                              "value": "128"
                            },
                            {
                              "name": "MAX_MATCHING_WINDOW",
                              "value": "1024"
                            },
                            {
                              "name": "DATA_BLOCK_DUMP_INTERVAL",
                              "value": "300"
                            },
                            {
                              "name": "DATA_BLOCK_DUMP_THRESHOLD",
                              "value": "202144"
                            },
                            {
                              "name": "EXAMPLE_ID_DUMP_INTERVAL",
                              "value": "600"
                            },
                            {
                              "name": "EXAMPLE_ID_DUMP_THRESHOLD",
                              "value": "262144"
                            },
                            {
                              "name": "EXAMPLE_ID_BATCH_SIZE",
                              "value": "4096"
                            },
                            {
                              "name": "MAX_FLYING_EXAMPLE_ID",
                              "value": "307152"
                            }
                          ],
                          "resources": {
                            "limits": {
                              "cpu": "18000m",
                              "memory": "12Gi"
                            },
                            "requests": {
                              "cpu": "18000m",
                              "memory": "12Gi"
                            }
                          }
                        }
                      ]
                    }
                  }
                }
              }
            }
          },
          "id": 4453,
          "name": "fl-360-join-job-v1",
          "job_type": "data_join",
          "client_ticket_name": "follower_ticket",
          "server_ticket_name": "ticket-360-k4",
          "user_id": 6,
          "k8s_meta_snapshot": null,
          "status": "stopped",
          "federation_id": 2,
          "created_at": "2020-09-11T06:57:01.000Z",
          "updated_at": "2020-09-11T06:57:01.000Z",
          "deleted_at": null
        }
      }
    ]
}