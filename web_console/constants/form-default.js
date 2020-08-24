// key is the key of form field
// value is the default value of field
const K8S_SETTINGS = {
  "storage_root_path": "data",
  "imagePullSecrets": [{"name": "regcred-bd"}],
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

for (let k in K8S_SETTINGS) {
  if (typeof K8S_SETTINGS[k] === 'object') {
    K8S_SETTINGS[k] = JSON.stringify(K8S_SETTINGS[k], null, 2)
  }
}

module.exports = {
  K8S_SETTINGS
}