# Build Redis as follows:
#
# - make               -- create non-SGX no-debug-log manifest
# - make SGX=1         -- create SGX no-debug-log manifest
# - make SGX=1 DEBUG=1 -- create SGX debug-log manifest
#
# Any of these invocations clones Redis' git repository and builds Redis in
# default configuration and in the latest-to-date (5.0.5) version.
#
# By default, Redis uses poll/epoll mechanism of Linux. To build Redis with
# select, use `make USE_SELECT=1`. For correct re-builds, always clean up
# Redis source code beforehand via `make distclean`.
#
# Use `make clean` to remove Graphene-generated files and `make distclean` to
# additionally remove the cloned Redis git repository.

################################# CONSTANTS ###################################

# Relative path to Graphene root
GRAPHENEDIR ?= ../../..
SGX_SIGNER_KEY ?= $(GRAPHENEDIR)/Pal/src/host/Linux-SGX/signer/enclave-key.pem
INSTALL_PREFIX ?= /usr/local
export PATH := $(INSTALL_PREFIX)/bin:$(PATH)

ifeq ($(DEBUG),1)
GRAPHENE_LOG_LEVEL = debug
else
GRAPHENE_LOG_LEVEL = error
endif

.PHONY: all
all: grpc-server.manifest
ifeq ($(SGX),1)
all: grpc-server.manifest.sgx grpc-server.token grpc-server.sig \
		grpc-async-server.manifest.sgx grpc-async-server.token grpc-async-server.sig \
		streaming-server.manifest.sgx streaming-server.token streaming-server.sig  \
		streaming-client.manifest.sgx streaming-client.token streaming-client.sig
endif

include $(GRAPHENEDIR)/Scripts/Makefile.configs

################################ gRPC MANIFEST ###############################

# The template file contains almost all necessary information to run grpc 
# under Graphene / Graphene-SGX. We create grpc-server.manifest (to be run under
# non-SGX Graphene) by simply replacing variables in the template file via sed.

%.manifest: %.manifest.template
	graphene-manifest \
		-Dlog_level=$(GRAPHENE_LOG_LEVEL) \
		-Darch_libdir=$(ARCH_LIBDIR) \
		$< > $@

# Manifest for Graphene-SGX requires special "graphene-sgx-sign" procedure. This procedure measures
# all Redis trusted files, adds the measurement to the resulting manifest.sgx file (among other,
# less important SGX options) and creates redis-server.sig (SIGSTRUCT object).
#
# Graphene-SGX requires EINITTOKEN and SIGSTRUCT objects (see SGX hardware ABI, in particular EINIT
# instruction). The "graphene-sgx-get-token" script generates EINITTOKEN based on a SIGSTRUCT and
# puts it in .token file. Note that filenames must be the same as the manifest name (i.e.,
# "redis-server"). EINITTOKEN must be generated on the machine where the application will run, not
# where it was built.

%.manifest.sgx: %.manifest
	graphene-sgx-sign \
		--key $(SGX_SIGNER_KEY) \
		--manifest $< \
		--output $@ 

%.sig: %.manifest.sgx
	@echo "go, go, go\n"

%.token: %.sig
	graphene-sgx-get-token --output $@ --sig $<

############################## RUNNING TESTS ##################################
.PHONY: start-native-server
start-native-server: all
	./grpc-server -ssl=1

ifeq ($(SGX),)
GRAPHENE = graphene-direct
else
GRAPHENE = graphene-sgx
endif

.PHONY: start-graphene-server
start-graphene-server: all
	$(GRAPHENE) grpc-server

################################## CLEANUP ####################################

.PHONY: clean
clean:
	$(RM) *.token *.sig *.manifest.sgx *.manifest

.PHONY: distclean
distclean: clean
	$(RM) -rf grpc .local

################################## RUN ####################################
run:
	graphene-sgx grpc-server
	
