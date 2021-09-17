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

#include <grpc/support/log.h>
#include <grpc/support/sync.h>
#include <grpcpp/security/server_credentials.h>
#include "grpc_sgx_ra_tls_utils.h"
#include "grpc_sgx_credentials_provider.h"

namespace grpc {
namespace sgx {

#define PEM_BEGIN_CRT           "-----BEGIN CERTIFICATE-----\n"
#define PEM_END_CRT             "-----END CERTIFICATE-----\n"


// Server side is required to use a provider, because server always needs to use identity certs.
::grpc_impl::experimental::TlsKeyMaterialsConfig::PemKeyCertPair get_cred_key_pair() {
        mbedtls_x509_crt srvcert;
  mbedtls_pk_context pkey;

  mbedtls_x509_crt_init(&srvcert);
  mbedtls_pk_init(&pkey);

  library_engine ra_tls_attest_lib("libra_tls_attest.so", RTLD_LAZY);
  auto ra_tls_create_key_and_crt_f = reinterpret_cast<int (*)(mbedtls_pk_context*, mbedtls_x509_crt*)>(ra_tls_attest_lib.get_func("ra_tls_create_key_and_crt"));

  int ret = (*ra_tls_create_key_and_crt_f)(&pkey, &srvcert);
  if (ret != 0) {
      throw std::runtime_error(std::string("ra_tls_create_key_and_crt failed and error %s\n\n", mbedtls_high_level_strerr(ret)));
  }

  unsigned char private_key_pem[16000], cert_pem[16000];
  size_t olen;

  ret = mbedtls_pk_write_key_pem(&pkey, private_key_pem, 16000);
  if (ret != 0) {
    throw std::runtime_error(std::string("something went wrong while extracting private key, %s\n\n", mbedtls_high_level_strerr(ret)));
  }

  ret = mbedtls_pem_write_buffer(PEM_BEGIN_CRT, PEM_END_CRT,
                                 srvcert.raw.p, srvcert.raw.len,
                                 cert_pem, 16000, &olen);
  if (ret != 0) {
    throw std::runtime_error(std::string("mbedtls_pem_write_buffer failed, error %s\n\n", mbedtls_high_level_strerr(ret)));
  };

  auto private_key = std::string((char*) private_key_pem);
  auto certificate_chain = std::string((char*) cert_pem);

  ::grpc_impl::experimental::TlsKeyMaterialsConfig::PemKeyCertPair pkcp = {private_key,
      certificate_chain};

  mbedtls_printf("Server key:\n%s\n", private_key_pem);
  mbedtls_printf("Server crt:\n%s\n", cert_pem);

  mbedtls_x509_crt_free(&srvcert);
  mbedtls_pk_free(&pkey);
  return pkcp;
}

typedef class ::grpc_impl::experimental::TlsKeyMaterialsConfig
TlsKeyMaterialsConfig;
typedef class ::grpc_impl::experimental::TlsCredentialReloadArg
TlsCredentialReloadArg;
typedef struct ::grpc_impl::experimental::TlsCredentialReloadInterface
TlsCredentialReloadInterface;
typedef class ::grpc_impl::experimental::TlsServerAuthorizationCheckArg
TlsServerAuthorizationCheckArg;
typedef struct ::grpc_impl::experimental::TlsServerAuthorizationCheckInterface
TlsServerAuthorizationCheckInterface;

class TestTlsCredentialReload : public TlsCredentialReloadInterface {
    int Schedule(TlsCredentialReloadArg* arg) override {
        if (!arg->is_pem_key_cert_pair_list_empty()) {
            arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_UNCHANGED);
            return 0;
        }
        GPR_ASSERT(arg != nullptr);
        auto key_pair = get_cred_key_pair();
        struct TlsKeyMaterialsConfig::PemKeyCertPair pair3 = { key_pair.private_key.c_str(),
            key_pair.cert_chain.c_str()};
        arg->set_pem_root_certs("new_pem_root_certs");
        arg->add_pem_key_cert_pair(pair3);
        arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_NEW);
        return 0;
    }

    void Cancel(TlsCredentialReloadArg* arg) override {
        GPR_ASSERT(arg != nullptr);
        arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_FAIL);
        arg->set_error_details("cancelled");
    }
};


class TestTlsServerAuthorizationCheck
: public TlsServerAuthorizationCheckInterface {
    int Schedule(TlsServerAuthorizationCheckArg* arg) override {
        GPR_ASSERT(arg != nullptr);
        return 0;
    }

    void Cancel(TlsServerAuthorizationCheckArg* arg) override {
        GPR_ASSERT(arg != nullptr);
        arg->set_status(GRPC_STATUS_PERMISSION_DENIED);
        arg->set_error_details("cancelled");
    }
};

std::shared_ptr<grpc::ServerCredentials> TlsServerCredentials() {
  using namespace ::grpc_impl::experimental;
  auto key_pair = get_cred_key_pair();

  auto provider = GetCredentialsProvider(key_pair.private_key, key_pair.cert_chain);
  auto server_creds = provider->GetServerCredentials(kTlsCredentialsType);
  auto processor = std::shared_ptr<AuthMetadataProcessor>();
  server_creds->SetAuthMetadataProcessor(processor);
  return server_creds;
};

}  // namespace sgx
}  // namespace grpc
