# Generate yamls
`make manifests` 

To generate yamls in ./config, such as ./config/crd/bases and ./config/rbac

在生成后需要在annotation中添加`api-approved.kubernetes.io: https://github.com/kubernetes/kubernetes/pull/78458`来避免k8s报警
# Test Controller locally
`make install `

To install Crd and RBAC in your cluster which specify in your .kube config.


`make run` 

Local run a Controller in your terminal which watch and update resources in the cluster of .kube.

# Run in cluster
`make docker-build docker-push IMG=<some-registry>/<project-name>:tag`
`make deploy IMG=<some-registry>/<project-name>:tag`

# Integration test
`make test`

# 后续开发
框架相关文档：https://book.kubebuilder.io/

仅需关注与修改/api/v1alpha1/fedapp_types.go（定义）和/contollers.fedapp_controller.go（控制逻辑）即可。

后续增加CRD和对应的Controller均统一在此目录(Project)下，参考文档中指令即可添加新的CRD脚手架。

# 集群依赖
- 0.1.2 版本以上使用了 非headless service，所以如果想要运行tensorflow，需要集群开启hairpin mode。