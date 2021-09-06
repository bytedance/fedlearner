# MNIST

This directory contains steps and artifacts to run a MNIST sample workload on
Graphene.

# Build docker image

```
cp build_docker_image.sh ../ && cd ..
./build_docker_image.sh ${tag}
```

# Run in container

## Test Mode
```
cd /graphene/Examples/mnist
test-sgx.sh data
test-sgx.sh leader
```

open another terminal and execute
```
test-sgx.sh follower 
```

# Features Not Supported 

* tensorflow-io, used by fedlearner but not provided, mocked by `sgx/tenorflow_io.py`
