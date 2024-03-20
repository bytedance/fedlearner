################################# CONSTANTS ###################################

GRAMINEDIR ?= ../../../..
SGX_SIGNER_KEY ?= $(GRAMINEDIR)/Pal/src/host/Linux-SGX/signer/enclave-key.pem

include $(GRAMINEDIR)/Scripts/Makefile.configs

ifeq ($(DEBUG),1)
GRAPHENE_LOG_LEVEL = debug
else
GRAPHENE_LOG_LEVEL = error
endif

.PHONY: all
all: grpc.manifest
ifeq ($(SGX),1)
all: grpc.manifest.sgx grpc.sig grpc.token
endif

################################ gRPC MANIFEST ###############################

grpc.manifest: grpc.manifest.template
	gramine-manifest \
		-Dentrypoint=$(GRAPHENE_ENTRYPOINT) \
		-Darch_libdir=$(ARCH_LIBDIR) \
		-Dlog_level=$(GRAPHENE_LOG_LEVEL) \
		$< >$@

grpc.manifest.sgx: grpc.manifest
	gramine-sgx-sign \
		--key $(SGX_SIGNER_KEY) \
		--manifest $< \
		--output $@

grpc.sig: grpc.manifest.sgx

grpc.token: grpc.sig
	gramine-sgx-get-token --output $@ --sig $<

################################## CLEANUP ####################################

.PHONY: clean
clean:
	$(RM) *.token *.sig *.manifest.sgx *.manifest
	$(RM) -r scripts/__pycache__

.PHONY: distclean
distclean: clean
