################################# CONSTANTS ###################################

GRAMINEDIR ?= ../..
SGX_SIGNER_KEY ?= $(GRAMINEDIR)/Pal/src/host/Linux-SGX/signer/enclave-key.pem

include $(GRAMINEDIR)/Scripts/Makefile.configs

ifeq ($(DEBUG),1)
GRAPHENE_LOG_LEVEL = debug
else
GRAPHENE_LOG_LEVEL = error
endif

.PHONY: all
all: python.manifest
ifeq ($(SGX),1)
all: python.manifest.sgx python.sig python.token
endif

################################ fedlearner MANIFEST ###############################

python.manifest: python.manifest.template
	gramine-manifest \
		-Dentrypoint=$(realpath $(shell sh -c "command -v python3")) \
		-Darch_libdir=$(ARCH_LIBDIR) \
		-Dlog_level=$(GRAPHENE_LOG_LEVEL) \
		$< >$@

python.manifest.sgx: python.manifest
	gramine-sgx-sign \
		--key $(SGX_SIGNER_KEY) \
		--manifest $< \
		--output $@

python.sig: python.manifest.sgx

python.token: python.sig
	gramine-sgx-get-token --output $@ --sig $<

################################## CLEANUP ####################################

.PHONY: clean
clean:
	$(RM) *.token *.sig *.manifest.sgx *.manifest
	$(RM) -r scripts/__pycache__

.PHONY: distclean
distclean: clean
