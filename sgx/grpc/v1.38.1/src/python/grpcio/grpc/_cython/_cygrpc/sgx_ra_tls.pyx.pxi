# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

cdef class SGXChannelCredentials(ChannelCredentials):

  def __cinit__(self,
                const char* config_json):
    # tls credentials options
    self.c_options = grpc_tls_credentials_options_create()

    # tls certificate provider
    cdef cppvector[cppstring] cpp_key_crt = grpc_sgx_ra_tls_get_key_cert()

    self.c_pairs = grpc_tls_identity_pairs_create();

    grpc_tls_identity_pairs_add_pair(
      self.c_pairs, cpp_key_crt[0].c_str(), cpp_key_crt[1].c_str())

    self.c_provider = grpc_tls_certificate_provider_static_data_create(NULL, self.c_pairs);

    grpc_tls_credentials_options_set_certificate_provider(self.c_options, self.c_provider)

    # grpc_tls_credentials_options_watch_root_certs(self.c_options)

    grpc_tls_credentials_options_watch_identity_key_cert_pairs(self.c_options)

    grpc_tls_credentials_options_set_cert_request_type(
      self.c_options, GRPC_SSL_REQUEST_AND_REQUIRE_CLIENT_CERTIFICATE_BUT_DONT_VERIFY)

    grpc_tls_credentials_options_set_root_cert_name(self.c_options, "")

    grpc_tls_credentials_options_set_identity_cert_name(self.c_options, "")

    # authorization check
    grpc_sgx_ra_tls_verify_init_with_config(config_json)

    grpc_tls_credentials_options_set_server_verification_option(
      self.c_options, GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION)

    self.c_check_config = grpc_tls_server_authorization_check_config_create(
      NULL, grpc_sgx_ra_tls_auth_check_schedule, NULL, NULL)

    grpc_tls_credentials_options_set_server_authorization_check_config(
      self.c_options, self.c_check_config)

  def __dealloc__(self):
    if self.c_pairs != NULL:
      grpc_tls_identity_pairs_destroy(self.c_pairs)
      self.c_pairs = NULL

    if self.c_provider != NULL:
      grpc_tls_certificate_provider_release(self.c_provider)
      self.c_provider = NULL

    if self.c_check_config != NULL:
      grpc_tls_server_authorization_check_config_release(self.c_check_config)
      self.c_check_config = NULL

  cdef grpc_channel_credentials *c(self) except *:
    return grpc_tls_credentials_create(self.c_options)


def channel_credentials_sgxratls(config_json):
  config_json = bytes(config_json, encoding = "ascii")
  return SGXChannelCredentials(config_json)

def server_credentials_sgxratls(config_json):
  # tls credentials options
  cdef grpc_tls_credentials_options *c_options = grpc_tls_credentials_options_create()

  # tls certificate provider
  cdef cppvector[cppstring] cpp_key_crt = grpc_sgx_ra_tls_get_key_cert()

  cdef grpc_tls_identity_pairs *c_pairs = grpc_tls_identity_pairs_create();

  grpc_tls_identity_pairs_add_pair(
    c_pairs, cpp_key_crt[0].c_str(), cpp_key_crt[1].c_str())

  grpc_tls_credentials_options_watch_identity_key_cert_pairs(c_options)

  # grpc_tls_credentials_options_watch_root_certs(c_options)

  cdef grpc_tls_certificate_provider *c_provider = \
    grpc_tls_certificate_provider_static_data_create(NULL, c_pairs);

  grpc_tls_credentials_options_set_certificate_provider(c_options, c_provider)

  grpc_tls_credentials_options_set_cert_request_type(
    c_options, GRPC_SSL_REQUEST_AND_REQUIRE_CLIENT_CERTIFICATE_BUT_DONT_VERIFY)

  grpc_tls_credentials_options_set_root_cert_name(c_options, "")

  grpc_tls_credentials_options_set_identity_cert_name(c_options, "")

  # authorization check
  config_json = bytes(config_json, encoding = "ascii")
  grpc_sgx_ra_tls_verify_init_with_config(config_json)

  grpc_tls_credentials_options_set_server_verification_option(
    c_options, GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION)

  cdef grpc_tls_server_authorization_check_config *c_check_config = \
    grpc_tls_server_authorization_check_config_create(NULL, grpc_sgx_ra_tls_auth_check_schedule, NULL, NULL)

  grpc_tls_credentials_options_set_server_authorization_check_config(
    c_options, c_check_config)

  # credentials
  cdef ServerCredentials credentials = ServerCredentials()
  credentials.c_credentials = grpc_tls_server_credentials_create(c_options)
  return credentials
