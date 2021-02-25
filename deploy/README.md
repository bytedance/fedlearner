# Fedlearner

您可以在一个 K8S 集群中快速尝试 Fedlearner 的基础功能，部署 Fedlearner 会在您的 K8S 集群中安装以下组件：

- fedlearner-stack 包含了 Fedlearner 所依赖的基础设施，包括 NFS Server/RDS (mariadb) 等；
- fedleaner 包含了运行 Fedlearner 任务所需的组件，包括 Fedlearner Operator/Fedlearner APIServer 和 Fedlearner WebConsole

请注意，Fedlearner Operator 目前仅适用于 K8S 1.14.8 - 1.16.9 版本 （推荐 1.16.9 的 K8S 版本），我们正在适配更新版本的 K8S。

## Prerequisite

Kubernetes 集群中的节点必须安装 `nfs-common` 依赖，例如：

```sh
apt install nfs-common
```

## Installation

### 安装 Fedlearner 基础设施

```sh
helm install fedlearner-stack ./deploy/charts/fedlearner-stack
cat <<EOF | kubectl apply -f -
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
 storageClassName: nfs
EOF
```

### 安装 Fedlearner Controller 和 CRD

```sh
export OPERATOR_IMAGE=`git rev-parse HEAD | cut -c 1-7`
helm install fedlearner ./deploy/charts/fedlearner \
    --set fedlearner-operator.ingress.enabled=false \
    --set fedlearner-operator.image.tag=$OPERATOR_IMAGE \
    --set fedlearner-operator.extraArgs.ingress-enabled-client-auth=false
kubectl create ns follower
helm install fedlearner ./deploy/charts/fedlearner --namespace follower \
    --set fedlearner-apiserver.enabled=false \
    --set fedlearner-web-console.enabled=false \
    --set fedlearner-operator.installCRD=false \
    --set fedlearner-operator.image.tag=$OPERATOR_IMAGE \
    --set fedlearner-operator.extraArgs.ingress-enabled-client-auth=false
```

### 运行测试任务

```
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
  namespace: default
stringData:
  ca.crt: fake
---
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
  namespace: follower
stringData:
  ca.crt: fake
EOF
kubectl create -f ./deploy/examples/normal_leader.yaml -f ./deploy/examples/normal_follower.yaml
```
