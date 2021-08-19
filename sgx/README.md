# MNIST

This directory contains steps and artifacts to run a MNIST sample workload on
Graphene.

# Build docker image and start container

```
cp build_docker_image.sh ../ && cd ..
./build_docker_image.sh ${tag}

cd sgx
./start_container.sh ${tag}
```

# Run in container

## Solo Mode
```
cd /graphene/Examples/mnist
test-sgx.sh data
test-sgx.sh leader
```

open another terminal and execute
```
test-sgx follower 
```

## Distributed Mode 


# Feature Not Included 

* tensorflow-io, imported by fedlearner but not installed, mocked by `sgx/tenorflow_io.py` 
