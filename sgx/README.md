# MNIST

This directory contains steps and artifacts to run a MNIST sample workload on
Graphene.

# Build docker image and start container

```
cd docker 
./build_docker_image.sh
./start_container.sh
```

# Run in container


```
cd /graphene/Examples/mnist
test-sgx.sh
```
