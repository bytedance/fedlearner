/*
 *
 * Copyright 2019 gRPC authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#ifndef GRPC_SGX_RA_TLS_UTILS_H
#define GRPC_SGX_RA_TLS_UTILS_H

#include <string>
#include <vector>
#include <memory>
#include <iostream>
#include <fstream>
#include <sstream>

#include <dlfcn.h>

#include <grpcpp/grpcpp.h>
#include <grpc/grpc_security.h>
#include <grpcpp/security/credentials.h>
#include <grpcpp/security/tls_credentials_options.h>
#include <grpcpp/security/server_credentials.h>

#define mbedtls_printf printf
#define mbedtls_fprintf fprintf

namespace grpc {
namespace sgx {

#include <mbedtls/config.h>
#include <mbedtls/certs.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/debug.h>
#include <mbedtls/entropy.h>
#include <mbedtls/error.h>
#include <mbedtls/net_sockets.h>
#include <mbedtls/ssl.h>
#include <mbedtls/x509.h>
#include <mbedtls/x509_crt.h>
#include <mbedtls/pk.h>
#include <mbedtls/pem.h>
#include <mbedtls/base64.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/rsa.h>

void hexdump_mem(const void*, size_t);

int parse_hex(const char*, void*, size_t);

class library_engine {
  public:
    library_engine();

    library_engine(const char*, int);

    ~library_engine();

    void open(const char*, int);

    void close();

    void* get_func(const char*);

    void* get_handle();

  private:
    void* handle;
    char* error;
};

}  // namespace sgx
}  // namespace grpc

#endif  // GRPC_SGX_RA_TLS_UTILS_H
