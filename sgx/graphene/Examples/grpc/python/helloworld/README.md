# gRPC

This directory contains the Makefile and the template manifest for the most
recent version of gRPC (as of this writing, version 3.18.0). This was tested
on a machine with SGX v1 and Ubuntu 18.04.

The Makefile and the template manifest contain extensive comments and are made
self-explanatory. Please review them to gain understanding of Graphene-SGX
and requirements for applications running under Graphene-SGX.

## gRPC RA-TLS server

The server is supposed to run in the SGX enclave with Graphene and RA-TLS dlopen-loaded. 

## gRPC RA-TLS client

If client is run without additional command-line arguments, it uses default RA-TLS verification
callback that compares `mr_enclave`, `mr_signer`, `isv_prod_id` and `isv_svn` against the corresonding
`RA_TLS_*` environment variables. To run the client with its own verification callback, execute it
with four additional command-line arguments (see the source code for details).

# Quick Start

```
./build.sh

kill %%

graphene-sgx python -u ./grpc-server.py &
graphene-sgx python -u ./grpc-client.py -id=x -svn=x -mrs=xxxxxxxxxxxxx -mre=xxxxxxxxxxxxx
```
