# Deploying Fedlearner on a Kubernetes Cluster

Fedlearner is not just a model trainer.
It also comes with surrounding infrastructures for cluster management,
job management, job monitoring, and network proxies.
This tutorial walks through the steps to deploy Fedlearner's job scheduler on
a Kubernetes cluster and submit model training jobs.

You will have two options: use a real K8s cluster or use local mock K8s cluster
with minikube. The later is recommended for local testing.

## Setup a K8s Cluster

To setup a local K8s cluster for testing, you fist need to install minikube.
See [this](https://kubernetes.io/docs/tasks/tools/install-minikube/)
page for instructions on minikube installation.
Minikube requires a VM driver.
We recommend hyperkit or docker as vm-driver for minikube.

After installation, run the following command to start minikube with
32 cores and 8GB of memory.
```
# replace DRIVER with hyperkit, docker, or other VMs you installed.
minikube start --cpus=32 --memory=8Gi --vm-driver=DRIVER
```

---
**NOTE**

Minikube will download images upon start.
For Chinese users, the default image repository could be very slow.
You can set the `--image-repository` option for faster mirrors.
See `minikube start --help` for more information.

---

Alternatively, please refer to the official
[documents](https://kubernetes.io/docs/setup/) for
information on setting up production K8s clusters.

## Deploy Fedlearner CRD on K8s

With an running K8s cluster, we can then deploy Fedlearner's CRD on
it.
CRDs are K8s addons that manage resources and jobs.

### Build Docker Image
First, we build a docker image for the CRD. In Fedlearner's root directory, run:
```
cd deploy
docker build -t fedlearner_operator:v1.0.0 .
```

For production K8s clusters, you need to push this image to appropriate
docker hub so that it can be pulled by pods later.

For minikube envirment, you need to set the docker client to point to
minikube's docker daemon _BEFORE_ you build the docker image:
```
eval $(minikube -p minikube docker-env)
```
Note that this is only effective for the current terminal session.

---
**NOTE**

docker needs to download base images from hub for build.
For Chinese users, the default docker hub could be very slow.
You can point docker to a different hub for faster download.

To do this, first ssh into minikube's shell:
```
minikube ssh
```

Then add your mirror's address to docker's config file:
```
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["URL"]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

You need to replace `URL` with the address to your mirror.
Aliyun's mirror is a good choice.
Please refer to [this](https://cr.console.aliyun.com/undefined/instances/mirrors)
page to get an address.
You may need to register an account first.

---

### Deploy CRD

With the CRD image in-place, we can now deploy it on to K8s:
```
kubectl create ns leader
kubectl create ns follower
kubectl create -f deploy/kubernetes_operator/manifests/service_account.yaml
kubectl apply -f deploy/kubernetes_operator/manifests/cluster_role.yaml
kubectl apply -f deploy/kubernetes_operator/manifests/cluster_role_binding.yaml
kubectl apply -f deploy/kubernetes_operator/manifests/fedlearner.k8s.io_flapps.yaml
kubectl apply -f deploy/kubernetes_operator/manifests/controller.yaml
```

Here, `leader` and `follower` are namespaces for the respective role.
In production setting, they should run on two different K8s clusters
in two data centers.
Here we run both on the same cluster for local testing.

Then, run the following commands to check if CRD was deployed successfully:
```
kubectl get pods -n leader -l app=flapp-operator
kubectl get pods -n follower -l app=flapp-operator
```

Optionally, you can run a test job to further verify your deployment.
Use the following commands to start a job that sleeps for 3 minutes and exits:
```
kubectl apply -f deploy/kubernetes_operator/manifests/normal_leader.yaml
kubectl apply -f deploy/kubernetes_operator/manifests/normal_follower.yaml
```

After a while, check that the job status is `FLStateComplete`:
```
kubectl get flapp normal -o json
```

## Deploy Fedlearner's Scheduler
