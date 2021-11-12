# FL on SGX

FL on SGX is a privacy-preserving federated machine learning framework. In this work, we implement remote attestation on GRPC and mbedTLS, and migrate Fedlearner (including Tensorflow) by LibOS to Intel SGX almost seamlessly.

# Build docker image

```
./build_docker_image.sh ${tag}
```

# Run in container

## Test Mode
```
cd ${gramine}/CI-Examples/mnist
test-ps-sgx.sh data
test-ps-sgx.sh make
test-ps-sgx.sh leader
```

open another terminal and execute
```
test-sgx.sh follower 
```

# Unsupported features

* tensorflow-io, used by fedlearner but not provided, mocked by `sgx/gramine/CI-Examples/tenorflow_io.py`
