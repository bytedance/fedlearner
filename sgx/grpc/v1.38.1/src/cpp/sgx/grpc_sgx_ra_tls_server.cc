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

#include "grpc_sgx_ra_tls_utils.h"

namespace grpc {
namespace sgx {

#define PEM_BEGIN_CRT           "-----BEGIN CERTIFICATE-----\n"
#define PEM_END_CRT             "-----END CERTIFICATE-----\n"

// Server side is required to use a provider, because server always needs to use identity certs.
std::vector<std::string> get_server_key_cert() {
  mbedtls_x509_crt srvcert;
  mbedtls_pk_context pkey;

  mbedtls_x509_crt_init(&srvcert);
  mbedtls_pk_init(&pkey);

  library_engine ra_tls_attest_lib("libra_tls_attest.so", RTLD_LAZY);
  auto ra_tls_create_key_and_crt_f =
    reinterpret_cast<int (*)(mbedtls_pk_context*, mbedtls_x509_crt*)>(
      ra_tls_attest_lib.get_func("ra_tls_create_key_and_crt"));

  int ret = (*ra_tls_create_key_and_crt_f)(&pkey, &srvcert);
  if (ret != 0) {
    throw std::runtime_error(
      std::string("ra_tls_create_key_and_crt_f error: %s\n", mbedtls_high_level_strerr(ret)));
  }

  unsigned char private_key_pem[16000], cert_pem[16000];
  size_t olen;

  ret = mbedtls_pk_write_key_pem(&pkey, private_key_pem, 16000);
  if (ret != 0) {
    throw std::runtime_error(
      std::string("mbedtls_pk_write_key_pem error: %s\n", mbedtls_high_level_strerr(ret)));
  }

  ret = mbedtls_pem_write_buffer(PEM_BEGIN_CRT, PEM_END_CRT,
                                 srvcert.raw.p, srvcert.raw.len,
                                 cert_pem, 16000, &olen);
  if (ret != 0) {
    throw std::runtime_error(
      std::string("mbedtls_pem_write_buffer error: %s\n", mbedtls_high_level_strerr(ret)));
  };

  std::vector<std::string> key_cert;
  key_cert.emplace_back(std::string((char*) private_key_pem));
  key_cert.emplace_back(std::string((char*) cert_pem));

  // grpc_printf("Server key:\n%s\n", private_key_pem);
  // grpc_printf("Server crt:\n%s\n", cert_pem);

  mbedtls_x509_crt_free(&srvcert);
  mbedtls_pk_free(&pkey);

  return key_cert;
};

std::vector<grpc::experimental::IdentityKeyCertPair> get_server_identity_key_cert_pairs(
    std::vector<std::string> key_cert) {
  grpc::experimental::IdentityKeyCertPair key_cert_pair;
  key_cert_pair.private_key = key_cert[0];
  key_cert_pair.certificate_chain = key_cert[1];

  std::vector<grpc::experimental::IdentityKeyCertPair> identity_key_cert_pairs;
  identity_key_cert_pairs.emplace_back(key_cert_pair);

  return identity_key_cert_pairs;
}

std::shared_ptr<grpc::ServerCredentials> TlsServerCredentials() {
  auto certificate_provider =
      std::make_shared<grpc::experimental::StaticDataCertificateProvider>(
          get_server_identity_key_cert_pairs(get_server_key_cert()));
  grpc::experimental::TlsServerCredentialsOptions options(certificate_provider);
  // options.set_certificate_provider(certificate_provider);
  options.set_root_cert_name("root_cert_name");
  options.set_identity_cert_name("identity_cert_name");
  options.set_cert_request_type(GRPC_SSL_DONT_REQUEST_CLIENT_CERTIFICATE);
  options.watch_identity_key_cert_pairs();
  return grpc::experimental::TlsServerCredentials(options);
};

}  // namespace sgx
}  // namespace grpc
