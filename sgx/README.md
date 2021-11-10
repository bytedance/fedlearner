# FL on SGX

FL on SGX is a privacy-preserving federated machine learning framework. In this work, we implement remote attestation on GRPC and mbedTLS, and migrate Fedlearner (including Tensorflow) by LibOS to Intel SGX almost seamlessly.

# Build docker image

```
cp build_docker_image.sh ../ && cd ..
./build_docker_image.sh ${tag}
```

# Run in container

## Test Mode
```
cd /gramine/Examples/mnist
test-sgx.sh data
test-sgx.sh leader
```

open another terminal and execute
```
test-sgx.sh follower 
```

# Unsupported features

* tensorflow-io, used by fedlearner but not provided, mocked by `sgx/tenorflow_io.py`
