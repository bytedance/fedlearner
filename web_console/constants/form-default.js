// key is the key of form field
// value is the default value of field
const K8S_SETTINGS = {
  "storage_root_path": "data",
  "imagePullSecrets": "regcred",
  "volumes": [
    {
      "persistentVolumeClaim": {
        "claimName": "pvc-fedlearner-default"
      },
      "name": "data"
    }
  ],
  "Env": [
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
  "volumeMounts": [
    {
      "mountPath": "/data",
      "name": "data"
    }
  ],
  "grpc_spec": {
    "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
    "authority": "external.name",
    "extraHeaders": {
      "x-host": "",
      "x-federation": "XFEDERATION"
    }
  },
  "leader_peer_spec": {
    "Follower": {
      "peerURL": "fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80",
      "authority": "external.name",
      "extraHeaders": {
        "x-host": "follower.flapp.operator"
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

const DATASOURCE_REPLICA_TYPE = ['Master', 'Worker']

const DATASOURCE_PUBLIC_PARAMS = {
  "Master": {
    "pair": true,
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
        "value": "portal_publish_dir/data-100wexamples-2"
      }
    ],
    "commend": [
      "/app/deploy/scripts/wait4pair_wrapper.sh"
    ],
    "args": [
      "/app/deploy/scripts/data_join/run_data_join_master.sh"
    ]
  },
  "Worker": {
    "pair": true,
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
    "commend": [
      "/app/deploy/scripts/wait4pair_wrapper.sh"
    ],
    "args": [
      "/app/deploy/scripts/data_join/run_data_join_master.sh"
    ]
  }
}

const DATASOURCE_JOB = {
  
}

const _ = [
  K8S_SETTINGS,
  DATASOURCE_PUBLIC_PARAMS.Master,
  DATASOURCE_PUBLIC_PARAMS.Worker
].forEach(el => {
  for (let k in el) {
    if (typeof el[k] === 'object') {
      el[k] = JSON.stringify(el[k], null, 2)
    }
  }
})

module.exports = {
  K8S_SETTINGS,
  DATASOURCE_REPLICA_TYPE,
  DATASOURCE_PUBLIC_PARAMS,
}