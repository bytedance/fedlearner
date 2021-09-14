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

#include <cassert>
#include "grpc_sgx_ra_tls_utils.h"

namespace grpc {
namespace sgx {

/*
RA-TLS: on client, only need to register ra_tls_verify_callback() for cert verification
  1. convert cert form pem format to der format
  2. extract SGX quote from "quote" OID extension from crt
  3. compare public key's hash from cert against quote's report_data
  4. prepare user-supplied verification parameter "allow outdated TCB"
  5. call into libsgx_dcap_quoteverify to verify ECDSA/based SGX quote
  6. verify all measurements from the SGX quote
*/

class TlsServerAuthorizationCheck;

static int (*ra_tls_verify_callback_f)(uint8_t* der_crt, size_t der_crt_size) = nullptr;

static std::shared_ptr<TlsServerAuthorizationCheck> server_authorization_check = nullptr;
static std::shared_ptr<grpc_impl::experimental::TlsServerAuthorizationCheckConfig> server_authorization_check_config = nullptr;

//static library_engine helper_sgx_urts_lib("libsgx_urts.so", RTLD_NOW | RTLD_GLOBAL);
//static library_engine ra_tls_verify_lib("libra_tls_verify_dcap.so", RTLD_LAZY);
static library_engine helper_sgx_urts_lib;//("libsgx_urts.so", RTLD_NOW | RTLD_GLOBAL);
static library_engine ra_tls_verify_lib;//("libra_tls_verify_dcap.so", RTLD_LAZY);


//static library_engine ra_tls_verify_lib("libra_tls_verify_dcap_graphene.so", RTLD_LAZY);

static char g_expected_mrenclave[32];
static char g_expected_mrsigner[32];
static char g_expected_isv_prod_id[2];
static char g_expected_isv_svn[2];

static bool g_verify_mrenclave   = true;
static bool g_verify_mrsigner    = true;
static bool g_verify_isv_prod_id = true;
static bool g_verify_isv_svn     = true;

static pthread_mutex_t g_print_lock;

void parse_args(const char* s_mrenclave, const char* s_mrsigner, const char* s_isv_prod_id, const char* s_isv_svn) {
  if (parse_hex(s_mrenclave, g_expected_mrenclave, sizeof(g_expected_mrenclave)) < 0) {
    mbedtls_printf("Cannot parse MRENCLAVE!\n");
    return;
  }

  if (parse_hex(s_mrsigner, g_expected_mrsigner, sizeof(g_expected_mrsigner)) < 0) {
    mbedtls_printf("Cannot parse MRSIGNER!\n");
    return;
  }

  errno = 0;
  uint16_t isv_prod_id = (uint16_t)strtoul(s_isv_prod_id, NULL, 10);
  if (errno) {
      mbedtls_printf("Cannot parse ISV_PROD_ID!\n");
      return;
  }
  memcpy(g_expected_isv_prod_id, &isv_prod_id, sizeof(isv_prod_id));

  errno = 0;
  uint16_t isv_svn = (uint16_t)strtoul(s_isv_svn, NULL, 10);
  if (errno) {
      mbedtls_printf("Cannot parse ISV_SVN\n");
      return;
  }
  memcpy(g_expected_isv_svn, &isv_svn, sizeof(isv_svn));
}

// RA-TLS: our own callback to verify SGX measurements
int ra_tls_verify_measurements_callback(const char* mrenclave, const char* mrsigner,
                                        const char* isv_prod_id, const char* isv_svn) {
    assert(mrenclave && mrsigner && isv_prod_id && isv_svn);

    pthread_mutex_lock(&g_print_lock);

    mbedtls_printf("MRENCLAVE\n"); 
    mbedtls_printf("    |- Expect :    "); hexdump_mem(g_expected_mrenclave, 32);
    mbedtls_printf("    |- Get    :    "); hexdump_mem(mrenclave, 32);
    mbedtls_printf("MRSIGNER\n");
    mbedtls_printf("    |- Expect :    "); hexdump_mem(g_expected_mrsigner, 32);
    mbedtls_printf("    |- Get    :    "); hexdump_mem(mrsigner, 32);
    mbedtls_printf("ISV_PROD_ID\n");
    mbedtls_printf("    |- Expect :    %hu\n", *((uint16_t*)g_expected_isv_prod_id));
    mbedtls_printf("    |- Get    :    %hu\n", *((uint16_t*)isv_prod_id));
    mbedtls_printf("ISV_SVN\n");
    mbedtls_printf("    |- Expect :    %hu\n", *((uint16_t*)g_expected_isv_svn));
    mbedtls_printf("    |- Get    :    %hu\n", *((uint16_t*)isv_svn));

    bool status = true;
    if (status && g_verify_mrenclave && memcmp(mrenclave, g_expected_mrenclave, sizeof(g_expected_mrenclave))) {
      status = false;
    }

    if (status && g_verify_mrsigner && memcmp(mrsigner, g_expected_mrsigner, sizeof(g_expected_mrsigner))) {
      status = false;
    }

    if (status && g_verify_isv_prod_id && memcmp(isv_prod_id, g_expected_isv_prod_id, sizeof(g_expected_isv_prod_id))) {
      status = false;
    }

    if (status && g_verify_isv_svn && memcmp(isv_svn, g_expected_isv_svn, sizeof(g_expected_isv_svn))) {
      status = false;
    }

    if (status) {
      mbedtls_printf("Quote Verify\n    |- Result :    Success\n");
      pthread_mutex_unlock(&g_print_lock);
      return 0;
    } else {
      mbedtls_printf("Quote Verify\n    |- Result :    Failed\n");
      pthread_mutex_unlock(&g_print_lock);
      return -1;
    }
}

void ra_tls_verify_init() {
    const char* in_enclave = getenv("TF_GRPC_TLS_ENABLE");
    if (in_enclave && in_enclave[0] == 'o') {
        ra_tls_verify_lib.open("libra_tls_verify_dcap_graphene.so", RTLD_LAZY);
    } else {
        helper_sgx_urts_lib.open("libsgx_urts.so", RTLD_NOW | RTLD_GLOBAL);
        ra_tls_verify_lib.open("libra_tls_verify_dcap.so", RTLD_LAZY);
    }
    ra_tls_verify_callback_f = reinterpret_cast<int (*)(uint8_t* der_crt, size_t der_crt_size)>(ra_tls_verify_lib.get_func("ra_tls_verify_callback_der"));

    auto ra_tls_set_measurement_callback_f = reinterpret_cast<void (*)(int (*f_cb)(const char *mrenclave,
                const char *mrsigner,
                const char *isv_prod_id,
                const char *isv_svn))>(ra_tls_verify_lib.get_func("ra_tls_set_measurement_callback"));
    (*ra_tls_set_measurement_callback_f)(ra_tls_verify_measurements_callback);
}

// test/cpp/client/credentials_test.cc : class TestTlsServerAuthorizationCheck
class TlsServerAuthorizationCheck
: public grpc_impl::experimental::TlsServerAuthorizationCheckInterface {
    int Schedule(grpc_impl::experimental::TlsServerAuthorizationCheckArg* arg) override {
        GPR_ASSERT(arg != nullptr);

        char cert_pem[16000];
        auto peer_cert_buf = arg->peer_cert();
        peer_cert_buf.copy(cert_pem, peer_cert_buf.length(), 0);

        int ret = (*ra_tls_verify_callback_f)(reinterpret_cast<uint8_t *>(cert_pem), 16000);
        if (ret != 0) {
            mbedtls_printf("something went wrong while verifying quote, code: %d\n", ret);
            arg->set_success(0);
            arg->set_status(GRPC_STATUS_UNAUTHENTICATED);
            return 0;
        } else {
            arg->set_success(1);
            arg->set_status(GRPC_STATUS_OK);
            return 0;
        }
    }

    void Cancel(grpc_impl::experimental::TlsServerAuthorizationCheckArg* arg) override {
        GPR_ASSERT(arg != nullptr);
        arg->set_status(GRPC_STATUS_PERMISSION_DENIED);
        arg->set_error_details("cancelled");
    }
};

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

typedef class ::grpc_impl::experimental::TlsCredentialReloadConfig TlsCredentialReloadConfig;

class TestTlsCredentialReload : public TlsCredentialReloadInterface {
    int Schedule(TlsCredentialReloadArg* arg) override {

        if (!arg->is_pem_key_cert_pair_list_empty()) {
            arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_UNCHANGED);
            return 0;
        }
        GPR_ASSERT(arg != nullptr);
        struct TlsKeyMaterialsConfig::PemKeyCertPair pair3 = {};
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

std::shared_ptr<grpc::ChannelCredentials> TlsCredentials(
        const char* mrenclave, const char* mrsigner,
        const char* isv_prod_id, const char* isv_svn) {
    parse_args(mrenclave, mrsigner, isv_prod_id, isv_svn);

    ra_tls_verify_init();

    server_authorization_check = std::make_shared<TlsServerAuthorizationCheck>();
    server_authorization_check_config = std::make_shared<grpc_impl::experimental::TlsServerAuthorizationCheckConfig>(
              server_authorization_check);
    grpc_impl::experimental::TlsCredentialsOptions options(
        GRPC_SSL_DONT_REQUEST_CLIENT_CERTIFICATE,
        GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION,
        nullptr,
        nullptr,
        server_authorization_check_config
    );

    return grpc_impl::experimental::TlsCredentials(options);

    /*
    grpc_tls_credentials_options* options = grpc_tls_credentials_options_create();
    grpc_tls_credentials_options_set_server_verification_option(options, GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION);

    server_authorization_check = std::make_shared<TlsServerAuthorizationCheck>();
    server_authorization_check_config = std::make_shared<grpc_impl::experimental::TlsServerAuthorizationCheckConfig>(
              server_authorization_check);
    grpc_tls_credentials_options_set_server_authorization_check_config(options, server_authorization_check_config);
    grpc_channel_credentials* creds = grpc_tls_credentials_create(options);
    return std::shared_ptr<grpc::ChannelCredentials>(
            new ::grpc::SecureChannelCredentials(std::move(creds)));
    */
};

std::shared_ptr<grpc::Channel> CreateSecureChannel(string target_str, std::shared_ptr<grpc::ChannelCredentials> channel_creds) {
    GPR_ASSERT(channel_creds.get() != nullptr);
    auto channel_args = grpc::ChannelArguments();
    channel_args.SetSslTargetNameOverride("RATLS");
    return grpc::CreateCustomChannel(target_str, std::move(channel_creds), channel_args);
};

}  // namespace sgx
}  // namespace grpc
