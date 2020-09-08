// key is the key of form field
// value is the default value of field
const K8S_SETTINGS = {
  "storage_root_path": "data",
  "imagePullSecrets": [{"name": "regcred"}],
  "env": [
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
      "x-host": "GRPC_X_HOST",
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

const RAW_DATA_CONTEXT = {
  file_wildcard: '*',
  batch_size: 1024,
  max_flying_item: 300000,
  merge_buffer_size: 4096,
  write_buffer_size: 10000000,
  resource_master_cpu_request: '1000m',
  resource_master_cpu_limit: '1000m',
  resource_master_memory_request: '2Gi',
  resource_master_memory_limit: '2Gi',
  input_data_format: 'CSV_DICT',
  output_data_format: 'TF_RECORD',
  compressed_type: 'None', // 'None' will be convert to empty string finally
}

for (let k in K8S_SETTINGS) {
  if (typeof K8S_SETTINGS[k] === 'object') {
    K8S_SETTINGS[k] = JSON.stringify(K8S_SETTINGS[k], null, 2)
  }
}

module.exports = {
  K8S_SETTINGS,
  RAW_DATA_CONTEXT,
}
