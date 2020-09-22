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
// This config determines how many parts to render in form
// Make sure to provide corresponding value in PARAMS config
const JOB_DATA_JOIN_REPLICA_TYPE = ['Master', 'Worker']
const JOB_PSI_DATA_JOIN_REPLICA_TYPE = ['Master', 'Worker']

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
          "replicas": 2,
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
        "Worker": {
          "replicas": 2,
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
        "Worker": {
          "replicas": 2,
          "template": {
            "spec": {
              "containers": [
                {
                  "resources": {
                    "limits": {
                      "cpu": "3000m",
                      "memory": "4Gi"
                    },
                    "requests": {
                      "cpu": "3000m",
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
  },
  "client_params":  {
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
          "replicas": 2,
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

// ************************************ datasouce ticket ************************************
// This config determines how many parts to render in form
// Make sure to provide corresponding value in PARAMS config
const TICKET_DATA_JOIN_REPLICA_TYPE = ['Master', 'Worker']
const TICKET_PSI_DATA_JOIN_REPLICA_TYPE = ['Master', 'Worker']

const TICKET_DATA_JOIN_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "pair": true,
          "replicas": 1,
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
                      "value": ""
                    }
                  ],
                  "image": "",
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
                  ]
                }
              ]
            }
          }
        },
        "Worker": {
          "pair": true,
          "replicas": 2,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "DATA_BLOCK_DUMP_INTERVAL",
                      "value": "600"
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
                      "value": "TF_RECORD"
                    }
                  ],
                  "image": "",
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
                  ]
                }
              ]
            }
          }
        }
      }
    }
  },
  "private_params": {}
}

const TICKET_PSI_DATA_JOIN_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "pair": true,
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
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
                      "value": ""
                    }
                  ],
                  "image": "",
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
                  ]
                }
              ]
            }
          }
        },
        "Worker": {
          "pair": true,
          "replicas": 2,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "PSI_RAW_DATA_ITER",
                      "value": "TF_RECORD"
                    },
                    {
                      "name": "PSI_OUTPUT_BUILDER",
                      "value": "TF_RECORD"
                    },
                    {
                      "name": "RAW_DATA_ITER",
                      "value": "TF_RECORD"
                    },
                    {
                      "name": "DATA_BLOCK_BUILDER",
                      "value": "TF_RECORD"
                    },
                    {
                      "name": "DATA_BLOCK_DUMP_INTERVAL",
                      "value": "600"
                    },
                    {
                      "name": "DATA_BLOCK_DUMP_THRESHOLD",
                      "value": "2000"
                    },
                    {
                      "name": "EXAMPLE_ID_DUMP_INTERVAL",
                      "value": "600"
                    },
                    {
                      "name": "EXAMPLE_ID_DUMP_THRESHOLD",
                      "value": "2000"
                    },
                    {
                      "name": "EXAMPLE_JOINER",
                      "value": "SORT_RUN_JOINER"
                    },
                    {
                      "name": "MAX_FLYING_EXAMPLE_ID",
                      "value": "307152"
                    },
                    {
                      "name": "MIN_MATCHING_WINDOW",
                      "value": "1024"
                    },
                    {
                      "name": "MAX_MATCHING_WINDOW",
                      "value": "8192"
                    },
                    {
                      "name": "INPUT_BASE_DIR",
                      "value": "/data/raw_data/mnist-tree/map_00000000"
                    },
                    {
                      "name": "RAW_DATA_SUB_DIR",
                      "value": ""
                    },
                    {
                      "name": "RSA_KEY_PATH",
                      "value": "/data/rsa_key/rsa_psi.pub"
                    },
                    {
                      "name": "PSI_PROCESS_BATCH_SIZE",
                      "value": "128"
                    },
                    {
                      "name": "OFFLOAD_PROCESSOR_NUMBER",
                      "value": "1"
                    },
                    {
                      "name": "MAX_FLYING_ITEM",
                      "value": "124102"
                    },
                    {
                      "name": "MAX_FLYING_SIGNED_BATCH",
                      "value": "1024"
                    },
                    {
                      "name": "MAX_FLYING_SIGN_RPC",
                      "value": "128"
                    },
                    {
                      "name": "SLOW_SIGN_THRESHOLD",
                      "value": "32"
                    },
                    {
                      "name": "SORT_RUN_MERGER_READ_AHEAD_BUFFER",
                      "value": "224288"
                    },
                    {
                      "name": "STUB_FANOUT",
                      "value": "4"
                    },
                    {
                      "name": "SIGN_RPC_TIMEOUT_MS",
                      "value": "128000"
                    }
                  ],
                  "image": "",
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
                    "/app/deploy/scripts/data_join/run_psi_data_join_follower_worker.sh"
                  ]
                }
              ]
            }
          }
        }
      }
    }
  },
  "private_params": {}
}
// ***************************************************************************************

// ************************************ taining job ************************************
// This config determines how many parts to render in form
// Make sure to provide corresponding value in PARAMS config
const JOB_NN_REPLICA_TYPE = ['Master', 'Worker']
const JOB_TREE_REPLICA_TYPE = ['Master', 'Worker']

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

// ************************************ taining ticket ************************************
// This config determines how many parts to render in form
// Make sure to provide corresponding value in PARAMS config
const TICKET_NN_REPLICA_TYPE = ['Master', 'Worker']
const TICKET_TREE_REPLICA_TYPE = ['Master', 'Worker']

const TICKET_NN_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Master": {
          "replicas": 1,
          "pair": false,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "DATA_SOURCE",
                      "value": ""
                    }
                  ],
                  "image": "",
                  "ports": [
                    {
                      "containerPort": 50051,
                      "name": "flapp-port"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/trainer/run_trainer_master.sh"
                  ]
                }
              ]
            }
          }
        },
        "PS": {
          "pair": false,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                  ],
                  "image": "",
                  "ports": [
                    {
                      "containerPort": 50051,
                      "name": "flapp-port"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/trainer/run_trainer_ps.sh"
                  ]
                }
              ]
            }
          }
        },
        "Worker": {
          "pair": true,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "CODE_KEY",
                      "value": ""
                    },
                    {
                      "name": "SAVE_CHECKPOINT_STEPS",
                      "value": "1000"
                    }
                  ],
                  "image": "",
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
                  ]
                }
              ]
            }
          }
        }
      }
    }
  },
  "private_params": {}
}

const TICKET_TREE_PARAMS = {
  "public_params": {
    "spec": {
      "flReplicaSpecs": {
        "Worker": {
          "pair": true,
          "replicas": 1,
          "template": {
            "spec": {
              "containers": [
                {
                  "env": [
                    {
                      "name": "DATA_PATH",
                      "value": ""
                    },
                    {
                      "name": "FILE_EXT",
                      "value": ".data"
                    },
                    {
                      "name": "SEND_SCORES_TO_FOLLOWER",
                      "value": ""
                    },
                    {
                      "name": "MODE",
                      "value": "train"
                    }
                  ],
                  "image": "",
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
                    "/app/deploy/scripts/trainer/run_tree_worker.sh"
                  ]
                }
              ]
            }
          }
        }
      }
    }
  },
  "private_params": {}
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
                    "limits": {
                      "cpu": "2000m",
                      "memory": "3Gi"
                    },
                    "requests": {
                      "cpu": "2000m",
                      "memory": "3Gi"
                    }
                  },
                  "image": "",
                  "ports": [
                    {
                      "containerPort": 50051,
                      "name": "flapp-port"
                    }
                  ],
                  "command": [
                    "/app/deploy/scripts/data_portal/run_data_portal_master.sh"
                  ],
                  "args": []
                }
              ]
            }
          }
        },
        "Worker": {
          "replicas": 2,
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
                  },
                  "image": "",
                  "command": [
                    "/app/deploy/scripts/data_portal/run_data_portal_worker.sh"
                  ],
                  "args": []
                }
              ]
            }
          }
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

  // datasource
  JOB_DATA_JOIN_REPLICA_TYPE,
  JOB_PSI_DATA_JOIN_REPLICA_TYPE,
  TICKET_DATA_JOIN_REPLICA_TYPE,
  TICKET_PSI_DATA_JOIN_REPLICA_TYPE,

  JOB_DATA_JOIN_PARAMS,
  JOB_PSI_DATA_JOIN_PARAMS,
  TICKET_DATA_JOIN_PARAMS,
  TICKET_PSI_DATA_JOIN_PARAMS,

  // training
  JOB_NN_REPLICA_TYPE,
  JOB_TREE_REPLICA_TYPE,
  TICKET_NN_REPLICA_TYPE,
  TICKET_TREE_REPLICA_TYPE,

  JOB_NN_PARAMS,
  JOB_TREE_PARAMS,
  TICKET_NN_PARAMS,
  TICKET_TREE_PARAMS,
}
