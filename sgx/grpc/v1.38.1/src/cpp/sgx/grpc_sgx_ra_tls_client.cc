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

/*
RA-TLS: on client, only need to register ra_tls_verify_callback() for cert verification
  1. extract SGX quote from "quote" OID extension from crt
  2. compare public key's hash from cert against quote's report_data
  3. prepare user-supplied verification parameter "allow outdated TCB"
  4. call into libsgx_dcap_quoteverify to verify ECDSA/based SGX quote
  5. verify all measurements from the SGX quote
*/

class TlsServerAuthorizationCheck;

static int (*ra_tls_verify_callback_f)(uint8_t* der_crt, size_t der_crt_size) = nullptr;

static std::shared_ptr<TlsServerAuthorizationCheck> server_authorization_check = nullptr;
static std::shared_ptr<grpc::experimental::TlsServerAuthorizationCheckConfig> server_authorization_check_config = nullptr;

static class library_engine helper_sgx_urts_lib;
static class library_engine ra_tls_verify_lib;

static char g_expected_mr_enclave[32];
static char g_expected_mr_signer[32];
static char g_expected_isv_prod_id[2];
static char g_expected_isv_svn[2];

static bool g_verify_mr_enclave   = true;
static bool g_verify_mr_signer    = true;
static bool g_verify_isv_prod_id  = true;
static bool g_verify_isv_svn      = true;

static pthread_mutex_t g_print_lock;

void parse_args(const char* s_mr_enclave, const char* s_mr_signer, const char* s_isv_prod_id, const char* s_isv_svn) {
  if (parse_hex(s_mr_enclave, g_expected_mr_enclave, sizeof(g_expected_mr_enclave)) < 0) {
    grpc_printf("Cannot parse mr_enclave!\n");
    return;
  }

  if (parse_hex(s_mr_signer, g_expected_mr_signer, sizeof(g_expected_mr_signer)) < 0) {
    grpc_printf("Cannot parse mr_signer!\n");
    return;
  }

  errno = 0;
  uint16_t isv_prod_id = (uint16_t)strtoul(s_isv_prod_id, NULL, 10);
  if (errno) {
    grpc_printf("Cannot parse isv_prod_id!\n");
    return;
  }
  memcpy(g_expected_isv_prod_id, &isv_prod_id, sizeof(isv_prod_id));

  errno = 0;
  uint16_t isv_svn = (uint16_t)strtoul(s_isv_svn, NULL, 10);
  if (errno) {
    grpc_printf("Cannot parse isv_svn\n");
    return;
  }
  memcpy(g_expected_isv_svn, &isv_svn, sizeof(isv_svn));
}

// RA-TLS: our own callback to verify SGX measurements
int ra_tls_verify_measurements_callback(const char* mr_enclave, const char* mr_signer,
                                        const char* isv_prod_id, const char* isv_svn) {
    assert(mr_enclave && mr_signer && isv_prod_id && isv_svn);

    pthread_mutex_lock(&g_print_lock);

    grpc_printf("mr_enclave\n"); 
    grpc_printf("    |- Expect :    "); hexdump_mem(g_expected_mr_enclave, 32);
    grpc_printf("    |- Get    :    "); hexdump_mem(mr_enclave, 32);
    grpc_printf("mr_signer\n");
    grpc_printf("    |- Expect :    "); hexdump_mem(g_expected_mr_signer, 32);
    grpc_printf("    |- Get    :    "); hexdump_mem(mr_signer, 32);
    grpc_printf("isv_prod_id\n");
    grpc_printf("    |- Expect :    %hu\n", *((uint16_t*)g_expected_isv_prod_id));
    grpc_printf("    |- Get    :    %hu\n", *((uint16_t*)isv_prod_id));
    grpc_printf("isv_svn\n");
    grpc_printf("    |- Expect :    %hu\n", *((uint16_t*)g_expected_isv_svn));
    grpc_printf("    |- Get    :    %hu\n", *((uint16_t*)isv_svn));

    bool status = true;
    if (status && g_verify_mr_enclave && memcmp(mr_enclave, g_expected_mr_enclave, sizeof(g_expected_mr_enclave))) {
      status = false;
    }

    if (status && g_verify_mr_signer && memcmp(mr_signer, g_expected_mr_signer, sizeof(g_expected_mr_signer))) {
      status = false;
    }

    if (status && g_verify_isv_prod_id && memcmp(isv_prod_id, g_expected_isv_prod_id, sizeof(g_expected_isv_prod_id))) {
      status = false;
    }

    if (status && g_verify_isv_svn && memcmp(isv_svn, g_expected_isv_svn, sizeof(g_expected_isv_svn))) {
      status = false;
    }

    if (status) {
      grpc_printf("quote Verify\n    |- Result :    Success\n");
      pthread_mutex_unlock(&g_print_lock);
      return 0;
    } else {
      grpc_printf("quote Verify\n    |- Result :    Failed\n");
      pthread_mutex_unlock(&g_print_lock);
      return -1;
    }
}

void ra_tls_verify_init(bool in_enclave = true) {
  if (in_enclave) {
    ra_tls_verify_lib.open("libra_tls_verify_dcap_graphene.so", RTLD_LAZY);
  } else {
    helper_sgx_urts_lib.open("libsgx_urts.so", RTLD_NOW | RTLD_GLOBAL);
    ra_tls_verify_lib.open("libra_tls_verify_dcap.so", RTLD_LAZY);
  }

  ra_tls_verify_callback_f =
    reinterpret_cast<int (*)(uint8_t* der_crt, size_t der_crt_size)>(
      ra_tls_verify_lib.get_func("ra_tls_verify_callback_der"));

  auto ra_tls_set_measurement_callback_f =
    reinterpret_cast<void (*)(int (*f_cb)(const char *mr_enclave,
                                          const char *mr_signer,
                                          const char *isv_prod_id,
                                          const char *isv_svn))>(
      ra_tls_verify_lib.get_func("ra_tls_set_measurement_callback"));
  (*ra_tls_set_measurement_callback_f)(ra_tls_verify_measurements_callback);
}

int server_auth_check_schedule(void* /* config_user_data */,
                               grpc_tls_server_authorization_check_arg* arg) {
  char der_crt[16000] = "";
  memcpy(der_crt, arg->peer_cert, strlen(arg->peer_cert));

  // char der_crt[16000] = TEST_CRT_PEM;
  // grpc_printf("%s\n", der_crt);

  int ret = (*ra_tls_verify_callback_f)(reinterpret_cast<uint8_t *>(der_crt), 16000);

  if (ret != 0) {
    grpc_printf("ra_tls_verify_callback_f error: %s\n", mbedtls_high_level_strerr(ret));
    arg->success = 0;
    arg->status = GRPC_STATUS_UNAUTHENTICATED;
  } else {
    arg->success = 1;
    arg->status = GRPC_STATUS_OK;
  }
  return 0; /* synchronous check */
}

// test/cpp/client/credentials_test.cc : class TestTlsServerAuthorizationCheck
class TlsServerAuthorizationCheck
    : public grpc::experimental::TlsServerAuthorizationCheckInterface {
  int Schedule(grpc::experimental::TlsServerAuthorizationCheckArg* arg) override {
    GPR_ASSERT(arg != nullptr);

    char der_crt[16000] = "";
    auto peer_cert_buf = arg->peer_cert();
    peer_cert_buf.copy(der_crt, peer_cert_buf.length(), 0);

    // char der_crt[16000] = TEST_CRT_PEM;
    // grpc_printf("%s\n", der_crt);

    int ret = (*ra_tls_verify_callback_f)(reinterpret_cast<uint8_t *>(der_crt), 16000);
    if (ret != 0) {
      grpc_printf("ra_tls_verify_callback_f error: %s\n", mbedtls_high_level_strerr(ret));
      arg->set_success(0);
      arg->set_status(GRPC_STATUS_UNAUTHENTICATED);
    } else {
      arg->set_success(1);
      arg->set_status(GRPC_STATUS_OK);
    }
    return 0; /* synchronous check */
  }

  void Cancel(grpc::experimental::TlsServerAuthorizationCheckArg* arg) override {
    GPR_ASSERT(arg != nullptr);
    arg->set_status(GRPC_STATUS_PERMISSION_DENIED);
    arg->set_error_details("cancelled");
  }
};

std::shared_ptr<grpc::ChannelCredentials> TlsCredentials(
    const char* mr_enclave, const char* mr_signer,
    const char* isv_prod_id, const char* isv_svn) {
  parse_args(mr_enclave, mr_signer, isv_prod_id, isv_svn);

  ra_tls_verify_init(true);

  grpc::experimental::TlsChannelCredentialsOptions options;
  options.set_server_verification_option(GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION);
  server_authorization_check = std::make_shared<TlsServerAuthorizationCheck>();
  server_authorization_check_config =
    std::make_shared<grpc::experimental::TlsServerAuthorizationCheckConfig>(server_authorization_check);
  options.set_server_authorization_check_config(server_authorization_check_config);

  return grpc::experimental::TlsCredentials(options);
};

std::shared_ptr<grpc::Channel> CreateSecureChannel(
    string target_str, std::shared_ptr<grpc::ChannelCredentials> channel_creds) {
  GPR_ASSERT(channel_creds.get() != nullptr);
  auto channel_args = grpc::ChannelArguments();
  channel_args.SetSslTargetNameOverride("RATLS");
  return grpc::CreateCustomChannel(target_str, std::move(channel_creds), channel_args);
};

}  // namespace sgx
}  // namespace grpc
