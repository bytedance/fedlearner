# Use one of the following commands to build the manifest for Python3:
#
# - make                Building for Linux
# - make DEBUG=1        Building for Linux (with Graphene debug output)
# - make SGX=1          Building for SGX
# - make SGX=1 DEBUG=1  Building for SGX (with Graphene debug output)
#
# Use `make clean` to remove Graphene-generated files.

include ../../Scripts/Makefile.configs

# Relative path to Graphene root
GRAPHENEDIR ?= ../..
SGX_SIGNER_KEY ?= $(GRAPHENEDIR)/Pal/src/host/Linux-SGX/signer/enclave-key.pem

ifeq ($(DEBUG),1)
GRAPHENE_LOG_LEVEL = debug
else
GRAPHENE_LOG_LEVEL = error
endif

GRAPHENE_LOG_FILE = graphene-sgx.log

.PHONY: all
all: python.manifest
ifeq ($(SGX),1)
all: python.manifest.sgx python.sig python.token
endif

python.manifest: python.manifest.template
	graphene-manifest \
		-Dlog_level=$(GRAPHENE_LOG_LEVEL) \
		-Dlog_file=$(GRAPHENE_LOG_FILE) \
		-Darch_libdir=$(ARCH_LIBDIR) \
		-Dentrypoint=$(realpath $(shell sh -c "command -v python3")) \
		$< >$@

# Python manifests for SGX:
#   Generating the SGX-specific manifest (python.manifest.sgx), the enclave signature,
#   and the token for enclave initialization.

python.manifest.sgx: python.manifest
	graphene-sgx-sign \
		--key $(SGX_SIGNER_KEY) \
		--manifest $< \
		--output $@

python.sig: python.manifest.sgx

python.token: python.sig
	graphene-sgx-get-token --output $@ --sig $<

.PHONY: clean
clean:
	$(RM) *.manifest *.manifest.sgx *.token *.sig OUTPUT* *.PID TEST_STDOUT TEST_STDERR
	$(RM) -r scripts/__pycache__

.PHONY: distclean
distclean: clean

.PHONY: run-native
run-native: all
	python3 -u model/lr.py

.PHONY: run-graphene
run-graphene: clean all
	taskset -c 0-7 graphene-sgx python -u model/lr.py

.PHONY: run-graphene-ps0
run-graphene-ps0: clean all
	taskset -c 0-7 graphene-sgx python -u model/end-2-end/train.py --task_index=0 --job_name=ps 

.PHONY: run-graphene-ps1
run-graphene-ps1: clean all
	taskset -c 8-15 graphene-sgx python -u model/end-2-end/train.py --task_index=1 --job_name=ps 

.PHONY: run-graphene-w0
run-graphene-w0: clean all
	taskset -c 16-23 graphene-sgx python -u model/end-2-end/train.py --task_index=0 --job_name=worker

.PHONY: run-graphene-w1
run-graphene-w1: clean all
	taskset -c 24-31 graphene-sgx python -u model/end-2-end/train.py --task_index=1 --job_name=worker
