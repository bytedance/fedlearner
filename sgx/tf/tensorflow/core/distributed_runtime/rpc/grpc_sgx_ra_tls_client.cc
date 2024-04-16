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
#include <mutex>
#include <unordered_map>

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

struct sgx_measurement {
  char mr_enclave[32];
  char mr_signer[32];
  uint16_t isv_prod_id;
  uint16_t isv_svn;
};

struct sgx_config {
  bool verify_in_enclave  = true;
  bool verify_mr_enclave  = true;
  bool verify_mr_signer   = true;
  bool verify_isv_prod_id = true;
  bool verify_isv_svn     = true;
  std::vector<sgx_measurement> sgx_mrs;
};

struct ra_tls_cache {
  int id = 0;
  std::unordered_map<int, std::shared_ptr<TlsServerAuthorizationCheck>> authorization_check;
  std::unordered_map<
      int, std::shared_ptr<grpc_impl::experimental::TlsServerAuthorizationCheckConfig>
    > authorization_check_config;
};

struct ra_tls_context {
  std::mutex mtx;
  struct sgx_config sgx_cfg;
  struct ra_tls_cache cache;
  class library_engine verify_lib;
  class library_engine sgx_urts_lib;
  int (*verify_callback_f)(uint8_t* der_crt, size_t der_crt_size) = nullptr;
};

struct ra_tls_context _ctx_;

sgx_config parse_sgx_config_json(const char *file)
{
    class json_engine sgx_json(file);
    struct sgx_config sgx_cfg;

    sgx_cfg.verify_in_enclave = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_in_enclave"), "on");
    sgx_cfg.verify_mr_enclave = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_mr_enclave"), "on");
    sgx_cfg.verify_mr_signer = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_mr_signer"), "on");
    sgx_cfg.verify_isv_prod_id = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_isv_prod_id"), "on");
    sgx_cfg.verify_isv_svn = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_isv_svn"), "on");

    mbedtls_printf("|- verify_in_enclave: %s\n", sgx_cfg.verify_in_enclave ? "on" : "off");
    mbedtls_printf("|- verify_mr_enclave: %s\n", sgx_cfg.verify_mr_enclave ? "on" : "off");
    mbedtls_printf("|- verify_mr_signer: %s\n", sgx_cfg.verify_mr_signer ? "on" : "off");
    mbedtls_printf("|- verify_isv_prod_id: %s\n", sgx_cfg.verify_isv_prod_id ? "on" : "off");
    mbedtls_printf("|- verify_isv_svn: %s\n", sgx_cfg.verify_isv_svn ? "on" : "off");

    auto objs = sgx_json.get_item(sgx_json.get_handle(), "sgx_mrs");
    auto obj_num = cJSON_GetArraySize(objs);

    sgx_cfg.sgx_mrs = std::vector<sgx_measurement>(obj_num, sgx_measurement());
    for (auto i = 0; i < obj_num; i++)
    {
        auto obj = cJSON_GetArrayItem(objs, i);
        mbedtls_printf("  |- expect measurement [%d]:\n", i + 1);
        auto mr_enclave = sgx_json.get_item_string(obj, "mr_enclave");
        mbedtls_printf("    |- mr_enclave: %s\n", mr_enclave);
        memset(sgx_cfg.sgx_mrs[i].mr_enclave, 0, sizeof(sgx_cfg.sgx_mrs[i].mr_enclave));
        auto res = parse_hex(mr_enclave, sgx_cfg.sgx_mrs[i].mr_enclave, sizeof(sgx_cfg.sgx_mrs[i].mr_enclave));
        if (!res){
          mbedtls_printf("mr_enclave invalid, %s\n", mr_enclave);
        }

        auto mr_signer = sgx_json.get_item_string(obj, "mr_signer");
        mbedtls_printf("    |- mr_signer: %s\n", mr_signer);
        memset(sgx_cfg.sgx_mrs[i].mr_signer, 0, sizeof(sgx_cfg.sgx_mrs[i].mr_signer));
        res = parse_hex(mr_signer, sgx_cfg.sgx_mrs[i].mr_signer, sizeof(sgx_cfg.sgx_mrs[i].mr_signer));
        if (!res){
          mbedtls_printf("mr_signer invalid, %s\n", mr_signer);
        }

        auto isv_prod_id = sgx_json.get_item_string(obj, "isv_prod_id");
        mbedtls_printf("    |- isv_prod_id: %s\n", isv_prod_id);
        sgx_cfg.sgx_mrs[i].isv_prod_id = strtoul(isv_prod_id ,nullptr, 10);

        auto isv_svn = sgx_json.get_item_string(obj, "isv_svn");
        mbedtls_printf("    |- isv_svn: %s\n", isv_svn);
        sgx_cfg.sgx_mrs[i].isv_svn = strtoul(isv_svn ,nullptr, 10);;
    };
    return sgx_cfg;
}

bool ra_tls_verify_measurement(const char* mr_enclave, const char* mr_signer,
                               const char* isv_prod_id, const char* isv_svn) {
  bool status = false;
  auto & sgx_cfg = _ctx_.sgx_cfg;
  for (auto & obj : sgx_cfg.sgx_mrs) {
    status = true;

    if (status && sgx_cfg.verify_mr_enclave && \
        memcmp(obj.mr_enclave, mr_enclave, 32)) {
      status = false;
    }

    if (status && sgx_cfg.verify_mr_signer && \
        memcmp(obj.mr_signer, mr_signer, 32)) {
      status = false;
    }

    if (status && sgx_cfg.verify_isv_prod_id && \
        (obj.isv_prod_id != *(uint16_t*)isv_prod_id)) {
      status = false;
    }

    if (status && sgx_cfg.verify_isv_svn && \
        (obj.isv_svn != *(uint16_t*)isv_svn)) {
      status = false;
    }

    if (status) {
      break;
    }
  }
  return status;
}

// RA-TLS: our own callback to verify SGX measurements
int ra_tls_verify_mr_callback(const char* mr_enclave, const char* mr_signer,
                              const char* isv_prod_id, const char* isv_svn) {
  std::lock_guard<std::mutex> lock(_ctx_.mtx);
  bool status = false;

  try {
    assert(mr_enclave && mr_signer && isv_prod_id && isv_svn);

    status = ra_tls_verify_measurement(mr_enclave, mr_signer, isv_prod_id, isv_svn);

    mbedtls_printf("MRENCLAVE\n"); 
    mbedtls_printf("    |- Get    :    "); hexdump_mem(mr_enclave, 32);
    mbedtls_printf("MRSIGNER\n");
    mbedtls_printf("    |- Get    :    "); hexdump_mem(mr_signer, 32);
    mbedtls_printf("ISV_PROD_ID\n");
    mbedtls_printf("    |- Get    :    %hu\n", *((uint16_t*)isv_prod_id));
    mbedtls_printf("ISV_SVN\n");
    mbedtls_printf("    |- Get    :    %hu\n", *((uint16_t*)isv_svn));

    if (status) {
      mbedtls_printf("Quote Verify\n    |- Result :    Success\n");
    } else {
      mbedtls_printf("Quote Verify\n    |- Result :    Failed\n");
    }

    fflush(stdout);
    return status ? 0 : -1;
  } catch (...) {
    mbedtls_printf("Unable to verify measurement!");
    fflush(stdout);
    return -1;
  }
}

void ra_tls_verify_init() {
  if (_ctx_.sgx_cfg.verify_in_enclave) {
    if (!_ctx_.verify_lib.get_handle()) {
      _ctx_.verify_lib.open("libra_tls_verify_dcap_gramine.so", RTLD_LAZY);
    }
  } else {
    if (!_ctx_.sgx_urts_lib.get_handle()) {
      _ctx_.sgx_urts_lib.open("libsgx_urts.so", RTLD_NOW | RTLD_GLOBAL);
    }
    if (!_ctx_.verify_lib.get_handle()) {
      _ctx_.verify_lib.open("libra_tls_verify_dcap.so", RTLD_LAZY);
    }
  }

  _ctx_.verify_callback_f =
    reinterpret_cast<int (*)(uint8_t* der_crt, size_t der_crt_size)>(
      _ctx_.verify_lib.get_func("ra_tls_verify_callback_der"));

  auto set_verify_mr_callback_f =
    reinterpret_cast<void (*)(int (*f_cb)(const char *mr_enclave,
                                          const char *mr_signer,
                                          const char *isv_prod_id,
                                          const char *isv_svn))>(
      _ctx_.verify_lib.get_func("ra_tls_set_measurement_callback"));
  (*set_verify_mr_callback_f)(ra_tls_verify_mr_callback);
}

void ra_tls_verify_init(const char* sgx_cfg_path) {
  std::lock_guard<std::mutex> lock(_ctx_.mtx);
  _ctx_.sgx_cfg = parse_sgx_config_json(sgx_cfg_path);
  ra_tls_verify_init();
}

typedef class ::grpc_impl::experimental::TlsServerAuthorizationCheckArg
TlsServerAuthorizationCheckArg;
typedef struct ::grpc_impl::experimental::TlsServerAuthorizationCheckInterface
TlsServerAuthorizationCheckInterface;
// typedef class ::grpc_impl::experimental::TlsKeyMaterialsConfig
// TlsKeyMaterialsConfig;
// typedef class ::grpc_impl::experimental::TlsCredentialReloadArg
// TlsCredentialReloadArg;
// typedef struct ::grpc_impl::experimental::TlsCredentialReloadInterface
// TlsCredentialReloadInterface;
// typedef class ::grpc_impl::experimental::TlsCredentialReloadConfig
// TlsCredentialReloadConfig;

// test/cpp/client/credentials_test.cc : class TestTlsServerAuthorizationCheck
class TlsServerAuthorizationCheck : public TlsServerAuthorizationCheckInterface {
    int Schedule(TlsServerAuthorizationCheckArg* arg) override {
        GPR_ASSERT(arg != nullptr);

        char cert_pem[16000];
        auto peer_cert_buf = arg->peer_cert();
        peer_cert_buf.copy(cert_pem, peer_cert_buf.length(), 0);

        int ret = (*_ctx_.verify_callback_f)(reinterpret_cast<uint8_t *>(cert_pem), 16000);
        if (ret != 0) {
            mbedtls_printf("something went wrong while verifying quote, error: %s\n", mbedtls_high_level_strerr(ret));
            arg->set_success(0);
            arg->set_status(GRPC_STATUS_UNAUTHENTICATED);
            return 0;
        } else {
            arg->set_success(1);
            arg->set_status(GRPC_STATUS_OK);
            return 0;
        }
    }

    void Cancel(TlsServerAuthorizationCheckArg* arg) override {
        GPR_ASSERT(arg != nullptr);
        arg->set_status(GRPC_STATUS_PERMISSION_DENIED);
        arg->set_error_details("cancelled");
    }
};

// class TestTlsCredentialReload : public TlsCredentialReloadInterface {
//     int Schedule(TlsCredentialReloadArg* arg) override {
//         if (!arg->is_pem_key_cert_pair_list_empty()) {
//             arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_UNCHANGED);
//             return 0;
//         }
//         GPR_ASSERT(arg != nullptr);
//         struct TlsKeyMaterialsConfig::PemKeyCertPair pair3 = {};
//         arg->set_pem_root_certs("new_pem_root_certs");
//         arg->add_pem_key_cert_pair(pair3);
//         arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_NEW);
//         return 0;
//     }

//     void Cancel(TlsCredentialReloadArg* arg) override {
//         GPR_ASSERT(arg != nullptr);
//         arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_FAIL);
//         arg->set_error_details("cancelled");
//     }
// };

std::shared_ptr<grpc::ChannelCredentials> TlsCredentials(const char* sgx_cfg_path) {

    ra_tls_verify_init(sgx_cfg_path);

    _ctx_.cache.id++;

    auto auth_check = _ctx_.cache.authorization_check.insert({
            _ctx_.cache.id, std::make_shared<TlsServerAuthorizationCheck>()
        }).first;

    auto auth_check_config = _ctx_.cache.authorization_check_config.insert({
            _ctx_.cache.id,
            std::make_shared<grpc_impl::experimental::TlsServerAuthorizationCheckConfig>(
                auth_check->second)
        }).first;

    grpc_impl::experimental::TlsCredentialsOptions options(
        GRPC_SSL_DONT_REQUEST_CLIENT_CERTIFICATE,
        GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION,
        nullptr,
        nullptr,
        auth_check_config->second
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

std::shared_ptr<grpc::Channel> CreateSecureChannel(
  string target_str, std::shared_ptr<grpc::ChannelCredentials> channel_creds) {
    GPR_ASSERT(channel_creds.get() != nullptr);
    auto channel_args = grpc::ChannelArguments();
    channel_args.SetSslTargetNameOverride("RATLS");
    return grpc::CreateCustomChannel(target_str, std::move(channel_creds), channel_args);
};

}  // namespace sgx
}  // namespace grpc
