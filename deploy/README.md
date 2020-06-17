# Fedlearner Operator

## Prerequisite

Kubernetes 集群中的节点必须安装 `nfs-common` 依赖，例如：

```sh
apt install nfs-common
```

## Installation

### 安装 Fedlearner 基础设施

```sh
helm install fedlearner-stack ./deploy/charts/fedlearner-stack
```

### 安装 Fedlearner Controller 和 CRD

```sh
kubectl create ns leader
helm install fedlearner ./deploy/charts/fedlearner --namespace leader
kubectl create ns follower
helm install fedlearner ./deploy/charts/fedlearner --namespace follower
kubectl apply -f ./deploy/charts/manifests/
```
