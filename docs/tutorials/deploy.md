# 部署

## Scheduler 部署

## K8s Controller 部署

`K8s Controller` 负责将 `Scheduler` 提交的任务部署到 K8s 上，并与 `FedLearner` 对端进行配对。
K8s 集群请见 `K8s 集群创建`，请确保 `kubectl` 可以正常工作。`K8s Controller` 部署包含以下步骤：
1. 创建 `namespace`，`kubectl create ns leader && kubectl create ns follower`
2. 创建 `K8s Controller` 所需的 `ServiceAccont`， `kubectl create deploy/kubernetes_operator/manifests/service_account.yaml`
3. 创建 `ClusterRole`，`kubectl apply -f deploy/kubernetes_operator/manifests/cluster_role.yaml`
4. 创建 `ClusterRoleBinding`，`kubectl apply -f deploy/kubernetes_operator/manifests/cluster_role_binding.yaml`
5. 创建 CRD， `kubectl apply -f deploy/kubernetes_operator/manifests/fedlearner.k8s.io_flapps.yaml`
6. 部署 `K8s Controller`， `kubectl apply -f deploy/kubernetes_operator/manifests/controller.yaml`，可以通过以下命令查看 `K8s Controller` 对应的 Pod：
`kubectl get pods -n leader -l app=flapp-operator`，`kubectl get pods -n follower -l app=flapp-operator`

### 打包镜像
将 Fedleader kubernetes operator 打包镜像
```bash
cd deploy/kubernetes_operator

export IMG=fedlearner_operator:2.1.1
make docker-build
make docker-push
```

### Quick Start Examples (Optional)

`deploy/kubernetes_operator/manifests` 包含了两个 `FedLearner` 样例，用于验证 `K8s Controller` 正常工作：
1. Normal exit example，`kubectl apply -f deploy/kubernetes_operator/manifests/normal_leader.yaml && kubectl apply -f deploy/kubernetes_operator/manifests/normal_follower.yaml`
命令会创建两个 `FLApp` （分别在 Leader 和 Follower namespace），Leader/Follower 在完成拉起后，休眠 3 分钟后会正常退出，可以通过 `kubectl get flapp normal -o json` 观察 `FLAppState` 最终状态为 `FLStateComplete`。
2. Abnormal exit example，`kubectl apply -f deploy/kubernetes_operator/manifests/abnormal_leader.yaml && kubectl apply -f deploy/kubernetes_operator/manifests/abnormal_follower.yaml`
命令会创建两个异常退出的 `FLApp`，`kubectl get flapp abnormal -o json` 命令可以看到最终 `FLAppState` 最终状态为 `FLStateFailed`。

### Debug Hint (Optional)

常见的 Debug 过程包括：
1. `kubectl logs` 观察 `K8s Controller` 报错日志。
2. 使用 `nicolaka/netshoot` 和 [`grpcurl`](https://github.com/fullstorydev/grpcurl) 测试网络问题。`deploy/kubernetes_operator/manifests` 中包含了用了 debug 的 netshoot.yaml，
可以通过 `kubectl apply -f deploy/kubernetes_operator/manifests/netshoot.yaml` 来启动一个 Pod，并通过 `kubectl exec` 命令进入到命令行中以测试网络的连通性。

## Proxy 部署