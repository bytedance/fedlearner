// key is the key of form field
// value is the default value of field
const K8S_SETTINGS = {
  "namespace": "default",
  "storage_root_path": "data",
  "imagePullSecrets": [{"name": "regcred"}],
  "env": [
    {
      "name": "ETCD_NAME",
      "value": "fedlearner",
    },
    {
      "name": "ETCD_BASE_DIR",
      "value": "fedlearner",
    },
    {
      "name": "ETCD_ADDR",
      "value": "fedlearner-stack-etcd.default.svc.cluster.local:2379"
    },
    {
      "name": "EGRESS_URL",
      "value": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80"
    },
    {
      "name": "EGRESS_HOST",
      "value": "external.name"
    }
  ],
  "grpc_spec": {
    "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
    "authority": "external.name",
    "extraHeaders": {
      "x-host": "default.flapp.webconsole",
      "x-federation": "XFEDERATION"
    }
  },
  "leader_peer_spec": {
    "Follower": {
      "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
      "authority": "external.name",
      "extraHeaders": {
        "x-host": "leader.flapp.operator"
      }
    }
  },
  "follower_peer_spec": {
    "Leader": {
      "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
      "authority": "external.name",
      "extraHeaders": {
        "x-host": "leader.flapp.operator"
      }
    }
  }
}

// ************************************ datasouce job ************************************
const DATASOURCE_JOB_REPLICA_TYPE = ['Master', 'Worker']

// inject to formMeta.client_params .server_params
const JOB_DATA_JOIN_PARAMS = {
  "server_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "3000m",
                      "memory": "1234Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
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
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    },
                    {
                      "name": "test-flag",
                      "value": "1234"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "1234m",
                      "memory": "5Gi"
                    },
                    "limits": {
                      "cpu": "6789m",
                      "memory": "10Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        }
      }
    }
  }
}

const JOB_PSI_DATA_JOIN_PARAMS = {
  "server_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "9876m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
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
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    },
                    {
                      "name": "test-flag",
                      "value": "7890"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TRAINNING_NAME",
                      "value": "test-train-1"
                    }
                  ],
                  "resources": {
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        }
      }
    }
  }
}
// ***************************************************************************************

// ************************************ datasouce ticket ************************************
const DATASOURCE_TICKET_REPLICA_TYPE = ['Master', 'Worker']

const TICKET_DATA_JOIN_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "pair": false,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "test-json"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_master.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "TF_RECORD"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  },
  "private_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50",
                  "env": [
                    {
                      "name": "RAW_DATA_SUB_DIR",
                      "value": "test-json"
                    },
                    {
                      "name": "PARTITION_NUM",
                      "value": "4"
                    }
                  ]
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  }
}

const TICKET_PSI_DATA_JOIN_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "TEST FLAG",
                      "value": "psi data join"
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
                      "value": "test-json"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_master.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "TF_RECORD"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  },
  "private_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50",
                  "env": [
                    {
                      "name": "RAW_DATA_SUB_DIR",
                      "value": "test-json"
                    },
                    {
                      "name": "PARTITION_NUM",
                      "value": "4"
                    }
                  ]
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  }
}
// ***************************************************************************************

// ************************************ taining job ************************************
const TRAINING_JOB_REPLICA_TYPE = ['Master', 'PS','Worker']

const JOB_NN_PARAMS = {
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
                      "memory": "2Gi"
                    },
                    "requests": {
                      "cpu": "1000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "PS": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
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
              ]
            }
          }
        },
        "Worker": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
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
                      "memory": "2Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "PS": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "limits": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "Worker": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "limits": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    }
                  }
                }
              ]
            }
          }
        }
      }
    }
  }
}

const JOB_TREE_PARAMS = {
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
                      "memory": "2Gi"
                    },
                    "requests": {
                      "cpu": "1000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "PS": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
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
              ]
            }
          }
        },
        "Worker": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
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
                      "memory": "2Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "2Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "PS": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "limits": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    }
                  }
                }
              ]
            }
          }
        },
        "Worker": {
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "limits": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "4Gi"
                    }
                  }
                }
              ]
            }
          }
        }
      }
    }
  }
}

// ***************************************************************************************

// ************************************ taining ticket ************************************
const TRAINING_TICKET_REPLICA_TYPE = ['Master', 'PS','Worker']

const TICKET_NN_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "test-json"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_master.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "TF_RECORD"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  },
  "private_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50",
                  "env": [
                    {
                      "name": "RAW_DATA_SUB_DIR",
                      "value": "test-json"
                    },
                    {
                      "name": "PARTITION_NUM",
                      "value": "4"
                    }
                  ]
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  }
}

const TICKET_TREE_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "test-json"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_master.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": "TF_RECORD"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/wait4pair_wrapper.sh"
                  ],
                  "args": [
                    "/app/deploy/scripts/data_join/run_data_join_worker.sh"
                  ],
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  },
  "private_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50",
                  "env": [
                    {
                      "name": "RAW_DATA_SUB_DIR",
                      "value": "test-json"
                    },
                    {
                      "name": "PARTITION_NUM",
                      "value": "4"
                    }
                  ]
                }
              ]
            }
          },
          "replicas": 1
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "image": "artifact.bytedance.com/fedlearner/fedlearner:049ad50"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  }
}
// ***************************************************************************************


// inject to formMeta.context
const RAW_DATA_CONTEXT = {
  "file_wildcard": "*",
  "input_data_format": "CSV_DICT",
  "output_data_format": "TF_RECORD",
  "compressed_type": "",
  "batch_size": 1024,
  "max_flying_item": 300000,
  "write_buffer_size": 10000000,
  "yaml_spec": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "requests": {
                      "cpu": "1000m",
                      "memory": "2Gi"
                    },
                    "limits": {
                      "cpu": "1000m",
                      "memory": "2Gi"
                    }
                  },
                  "image": "/"
                }
              ]
            }
          }
        },
        "Worker": {
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "limits": {
                      "cpu": "1000m",
                      "memory": "2Gi"
                    },
                    "requests": {
                      "memory": "2Gi"
                    }
                  },
                  "image": "/"
                }
              ]
            }
          },
          "replicas": 4
        }
      }
    }
  }
}


const _ = [
  K8S_SETTINGS,
].forEach(el => {
  for (let k in el) {
    if (typeof el[k] === 'object') {
      el[k] = JSON.stringify(el[k], null, 2)
    }
  }
})

module.exports = {
  K8S_SETTINGS,

  RAW_DATA_CONTEXT,

  DATASOURCE_TICKET_REPLICA_TYPE,
  TRAINING_TICKET_REPLICA_TYPE,
  DATASOURCE_JOB_REPLICA_TYPE,
  TRAINING_JOB_REPLICA_TYPE,

  JOB_DATA_JOIN_PARAMS,
  JOB_PSI_DATA_JOIN_PARAMS,
  TICKET_DATA_JOIN_PARAMS,
  TICKET_PSI_DATA_JOIN_PARAMS,

  JOB_NN_PARAMS,
  JOB_TREE_PARAMS,
  TICKET_NN_PARAMS,
  TICKET_TREE_PARAMS,
}
