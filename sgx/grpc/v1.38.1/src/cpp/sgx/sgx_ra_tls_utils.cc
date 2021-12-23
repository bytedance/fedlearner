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

#include "sgx_ra_tls_utils.h"

namespace grpc {
namespace sgx {

static struct ra_tls_context ra_tls_ctx;

bool hex_to_byte(const char *src, char *dst, size_t dst_size) {
  if (strlen(src) < dst_size*2) {
    return false;
  } else {
    for (auto i = 0; i < dst_size; i++) {
      if (!isxdigit(src[i*2]) || !isxdigit(src[i*2+1])) {
        return false;
      } else {
        sscanf(src+i*2, "%02hhx", dst+i);
      }
    }
    return true;
  }
};

void byte_to_hex(const char *src, char *dst, size_t src_size) {
  for (auto i = 0; i < src_size; i++) {
    sprintf(dst+i*2, "%02hhx", src[i]);
  }
};

std::string byte_to_hex(const char *src, size_t src_size) {
  char dst[src_size*2];
  memset(dst, 0, sizeof(dst));
  byte_to_hex(src, dst, src_size);
  return std::string(dst);
};

library_engine::library_engine() : handle(nullptr), error(nullptr) {};

library_engine::library_engine(const char* file, int mode) : handle(nullptr), error(nullptr) {
  this->open(file, mode);
}

library_engine::~library_engine() {
  this->close();
}

void library_engine::open(const char* file, int mode) {
  this->close();
  handle = dlopen(file, mode);
  error = dlerror();
  if (error != nullptr || handle == nullptr) {
    throw std::runtime_error("dlopen " + std::string(file) + " error, " + std::string(error));
  }
}

void library_engine::close() {
  if (handle) {
    dlclose(handle);
  }
  handle = nullptr;
  error = nullptr;
}

void* library_engine::get_func(const char* name) {
  auto func = dlsym(handle, name);
  error = dlerror();
  if (error != nullptr || func == nullptr) {
    throw std::runtime_error("dlsym " + std::string(name) + " error, " + std::string(error));
    return nullptr;
  } else {
    return func;
  }
}

void* library_engine::get_handle() {
  return handle;
}

json_engine::json_engine() : handle(nullptr) {};

json_engine::json_engine(const char* file) : handle(nullptr){
  this->open(file);
}

json_engine::~json_engine() {
  this->close();
}

bool json_engine::open(const char* file) {
  if (!file) {
    grpc_printf("wrong json file path\n");
    return false;
  }

  this->close();

  auto file_ptr = fopen(file, "r");
  fseek(file_ptr, 0, SEEK_END);
  auto length = ftell(file_ptr);
  fseek(file_ptr, 0, SEEK_SET);
  auto buffer = malloc(length);
  fread(buffer, 1, length, file_ptr);
  fclose(file_ptr);

  this->handle = cJSON_Parse((const char *)buffer);

  free(buffer);
  buffer = nullptr;

  if (this->handle) {
    return true;
  } else {
    grpc_printf("cjson open %s error: %s", file, cJSON_GetErrorPtr());
    return false;
  }
}

void json_engine::close() {
  if (this->handle) {
    cJSON_Delete(this->handle);
    this->handle = nullptr;
  }
}

cJSON * json_engine::get_handle() {
  return this->handle;
}

cJSON * json_engine::get_item(cJSON *obj, const char *item) {
  return cJSON_GetObjectItem(obj, item);
};

char * json_engine::print_item(cJSON *obj) {
  return cJSON_Print(obj);
};

bool json_engine::compare_item(cJSON *obj, const char *item) {
  auto obj_item = this->print_item(obj);
  return strncmp(obj_item+1, item, std::min(strlen(item), strlen(obj_item)-2)) == 0;
};

sgx_config parse_sgx_config_json(const char* file) {
  class json_engine sgx_json(file);
  struct sgx_config sgx_cfg;

  sgx_cfg.verify_in_enclave = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_in_enclave"), "on");
  sgx_cfg.verify_mr_enclave = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_mr_enclave"), "on");
  sgx_cfg.verify_mr_signer = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_mr_signer"), "on");
  sgx_cfg.verify_isv_prod_id = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_isv_prod_id"), "on");
  sgx_cfg.verify_isv_svn = sgx_json.compare_item(sgx_json.get_item(sgx_json.get_handle(), "verify_isv_svn"), "on");
  // grpc_printf("%d, %d, %d, %d, %d\n", sgx_cfg.verify_in_enclave,
  //                                     sgx_cfg.verify_mr_enclave,
  //                                     sgx_cfg.verify_mr_signer,
  //                                     sgx_cfg.verify_isv_prod_id,
  //                                     sgx_cfg.verify_isv_svn);

  auto objs = sgx_json.get_item(sgx_json.get_handle(), "sgx_mrs");
  auto obj_num = cJSON_GetArraySize(objs);

  sgx_cfg.sgx_mrs = std::vector<sgx_measurement>(obj_num, sgx_measurement());
  for (auto i = 0; i < obj_num; i++) {
    auto obj = cJSON_GetArrayItem(objs, i);

    auto mr_enclave = sgx_json.print_item(sgx_json.get_item(obj, "mr_enclave"));
    memset(sgx_cfg.sgx_mrs[i].mr_enclave, 0, sizeof(sgx_cfg.sgx_mrs[i].mr_enclave));
    hex_to_byte(mr_enclave+1, sgx_cfg.sgx_mrs[i].mr_enclave, sizeof(sgx_cfg.sgx_mrs[i].mr_enclave));

    auto mr_signer = sgx_json.print_item(sgx_json.get_item(obj, "mr_signer"));
    memset(sgx_cfg.sgx_mrs[i].mr_signer, 0, sizeof(sgx_cfg.sgx_mrs[i].mr_signer));
    hex_to_byte(mr_signer+1, sgx_cfg.sgx_mrs[i].mr_signer, sizeof(sgx_cfg.sgx_mrs[i].mr_signer));

    auto isv_prod_id = sgx_json.print_item(sgx_json.get_item(obj, "isv_prod_id"));
    sgx_cfg.sgx_mrs[i].isv_prod_id = strtoul(isv_prod_id, nullptr, 10);

    auto isv_svn = sgx_json.print_item(sgx_json.get_item(obj, "isv_svn"));
    sgx_cfg.sgx_mrs[i].isv_svn = strtoul(isv_svn, nullptr, 10);

    // grpc_printf("%s, %s, %s, %s\n", mr_enclave, mr_signer, isv_prod_id, isv_svn);
  };
  return sgx_cfg;
}

int TlsAuthorizationCheck::Schedule(grpc::experimental::TlsServerAuthorizationCheckArg* arg) {
  GPR_ASSERT(arg != nullptr);

  char der_crt[16000] = "";
  auto peer_cert_buf = arg->peer_cert();
  peer_cert_buf.copy(der_crt, peer_cert_buf.length(), 0);

  // char der_crt[16000] = TEST_CRT_PEM;
  // grpc_printf("%s\n", der_crt);

  int ret = (*ra_tls_ctx.ra_tls_verify_callback_f)(reinterpret_cast<uint8_t *>(der_crt), 16000);

  if (ret != 0) {
    grpc_printf("something went wrong while verifying quote\n");
    arg->set_success(0);
    arg->set_status(GRPC_STATUS_UNAUTHENTICATED);
  } else {
    arg->set_success(1);
    arg->set_status(GRPC_STATUS_OK);
  }
  return 0; /* synchronous check */
};

void TlsAuthorizationCheck::Cancel(grpc::experimental::TlsServerAuthorizationCheckArg* arg) {
  GPR_ASSERT(arg != nullptr);
  arg->set_status(GRPC_STATUS_PERMISSION_DENIED);
  arg->set_error_details("cancelled");
};

bool ra_tls_verify_measurement(const char* mr_enclave, const char* mr_signer,
                               const char* isv_prod_id, const char* isv_svn) {
  bool status = false;
  auto & sgx_cfg = ra_tls_ctx.sgx_cfg;
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

    if (status && sgx_cfg.verify_isv_prod_id && (*(uint16_t*)isv_prod_id) != obj.isv_prod_id) {
      status = false;
    }

    if (status && sgx_cfg.verify_isv_svn && (*(uint16_t*)isv_svn) != obj.isv_svn) {
      status = false;
    }

    if (status) {
      break;
    }
  }
  return status;
}

// RA-TLS: our own callback to verify SGX measurements
int ra_tls_verify_measurements_callback(const char* mr_enclave, const char* mr_signer,
                                        const char* isv_prod_id, const char* isv_svn) {
  assert(mr_enclave && mr_signer && isv_prod_id && isv_svn);

  bool status = ra_tls_verify_measurement(mr_enclave, mr_signer, isv_prod_id, isv_svn);

  grpc_printf("remote sgx measurements\n"); 
  grpc_printf("  |- mr_enclave     :  %s\n", byte_to_hex(mr_enclave, 32).c_str());
  grpc_printf("  |- mr_signer      :  %s\n", byte_to_hex(mr_signer, 32).c_str());
  grpc_printf("  |- isv_prod_id    :  %hu\n", *((uint16_t*)isv_prod_id));
  grpc_printf("  |- isv_svn        :  %hu\n", *((uint16_t*)isv_svn));

  if (status) {
    grpc_printf("  |- verify result  :  success\n");
  } else {
    grpc_printf("  |- verify result  :  failed\n");
  }

  fflush(stdout);

  return status ? 0 : -1;
}

void ra_tls_verify_init() {
  if (ra_tls_ctx.sgx_cfg.verify_in_enclave) {
    if (!ra_tls_ctx.verify_lib.get_handle()) {
      ra_tls_ctx.verify_lib.open("libra_tls_verify_dcap_gramine.so", RTLD_LAZY);
    }
  } else {
    if (!ra_tls_ctx.sgx_urts_lib.get_handle()) {
      ra_tls_ctx.sgx_urts_lib.open("libsgx_urts.so", RTLD_NOW | RTLD_GLOBAL);
    }
    if (!ra_tls_ctx.verify_lib.get_handle()) {
      ra_tls_ctx.verify_lib.open("libra_tls_verify_dcap.so", RTLD_LAZY);
    }
  }

  ra_tls_ctx.ra_tls_verify_callback_f =
    reinterpret_cast<int (*)(uint8_t* der_crt, size_t der_crt_size)>(
      ra_tls_ctx.verify_lib.get_func("ra_tls_verify_callback_der"));

  auto ra_tls_set_measurement_callback_f =
    reinterpret_cast<void (*)(int (*)(const char *mr_enclave,
                                      const char *mr_signer,
                                      const char *isv_prod_id,
                                      const char *isv_svn))>(
      ra_tls_ctx.verify_lib.get_func("ra_tls_set_measurement_callback"));
  (*ra_tls_set_measurement_callback_f)(ra_tls_verify_measurements_callback);
}

void ra_tls_verify_init(const char* file) {
  std::lock_guard<std::mutex> lock(ra_tls_ctx.mtx);
  ra_tls_ctx.sgx_cfg = parse_sgx_config_json(file);
  ra_tls_verify_init();
}

void ra_tls_verify_init(sgx_config sgx_cfg) {
  std::lock_guard<std::mutex> lock(ra_tls_ctx.mtx);
  ra_tls_ctx.sgx_cfg = sgx_cfg;
  ra_tls_verify_init();
}

// Require to use a provider, because server always needs to use identity certs.
std::vector<std::string> ra_tls_get_key_cert() {
  if (!ra_tls_ctx.attest_lib.get_handle()) {
    ra_tls_ctx.attest_lib.open("libra_tls_attest.so", RTLD_LAZY);
  }

  auto ra_tls_create_key_and_crt_f =
    reinterpret_cast<int (*)(mbedtls_pk_context*, mbedtls_x509_crt*)>(
      ra_tls_ctx.attest_lib.get_func("ra_tls_create_key_and_crt"));

  std::string error = "";
  std::vector<std::string> key_cert;

  mbedtls_x509_crt srvcert;
  mbedtls_pk_context pkey;

  mbedtls_x509_crt_init(&srvcert);
  mbedtls_pk_init(&pkey);

  int ret = (*ra_tls_create_key_and_crt_f)(&pkey, &srvcert);
  if (ret != 0) {
    error = "ra_tls_get_key_cert->mbedtls_pk_write_key_pem";
    goto out;
  }

  unsigned char private_key_pem[16000], cert_pem[16000];
  size_t olen;

  ret = mbedtls_pk_write_key_pem(&pkey, private_key_pem, 16000);
  if (ret != 0) {
    error = "ra_tls_get_key_cert->mbedtls_pk_write_key_pem";
    goto out;
  }

  ret = mbedtls_pem_write_buffer(PEM_BEGIN_CRT, PEM_END_CRT,
                                 srvcert.raw.p, srvcert.raw.len,
                                 cert_pem, 16000, &olen);
  if (ret != 0) {
    error = "ra_tls_get_key_cert->mbedtls_pem_write_buffer";
    goto out;
  };

  key_cert.emplace_back(std::string((char*) private_key_pem));
  key_cert.emplace_back(std::string((char*) cert_pem));

  // grpc_printf("Server key:\n%s\n", private_key_pem);
  // grpc_printf("Server crt:\n%s\n", cert_pem);

  out:
    mbedtls_x509_crt_free(&srvcert);
    mbedtls_pk_free(&pkey);

    if (ret != 0) {
      throw std::runtime_error(
            std::string((error + std::string(" failed: %s\n")).c_str(), mbedtls_high_level_strerr(ret)));
    }

  return key_cert;
};

int ra_tls_auth_check_schedule(void* /* confiuser_data */,
                               grpc_tls_server_authorization_check_arg* arg) {
  char der_crt[16000] = "";
  memcpy(der_crt, arg->peer_cert, strlen(arg->peer_cert));

  // char der_crt[16000] = TEST_CRT_PEM;
  // grpc_printf("%s\n", der_crt);

  int ret = (*ra_tls_ctx.ra_tls_verify_callback_f)(reinterpret_cast<uint8_t *>(der_crt), 16000);

  if (ret != 0) {
    grpc_printf("something went wrong while verifying quote\n");
    arg->success = 0;
    arg->status = GRPC_STATUS_UNAUTHENTICATED;
  } else {
    arg->success = 1;
    arg->status = GRPC_STATUS_OK;
  }
  return 0; /* synchronous check */
}

std::vector<grpc::experimental::IdentityKeyCertPair> get_identity_key_cert_pairs(
    std::vector<std::string> key_cert) {
  grpc::experimental::IdentityKeyCertPair key_cert_pair;
  key_cert_pair.private_key = key_cert[0];
  key_cert_pair.certificate_chain = key_cert[1];

  std::vector<grpc::experimental::IdentityKeyCertPair> identity_key_cert_pairs;
  identity_key_cert_pairs.emplace_back(key_cert_pair);
  return identity_key_cert_pairs;
}

void credential_option_set_authorization_check(
    grpc::sgx::CredentialsOptions& options) {
  std::lock_guard<std::mutex> lock(ra_tls_ctx.mtx);

  if (!ra_tls_ctx.authorization_check) {
    ra_tls_ctx.authorization_check = std::make_shared<TlsAuthorizationCheck>();
  }

  if (!ra_tls_ctx.authorization_check_config) {
    ra_tls_ctx.authorization_check_config =
      std::make_shared<grpc::experimental::TlsServerAuthorizationCheckConfig>(
        ra_tls_ctx.authorization_check);
  }

  options.set_verification_option(GRPC_TLS_SKIP_ALL_SERVER_VERIFICATION);
  options.set_authorization_check_config(ra_tls_ctx.authorization_check_config);
}

void credential_option_set_certificate_provider(grpc::sgx::CredentialsOptions& options) {
  std::lock_guard<std::mutex> lock(ra_tls_ctx.mtx);

  if (!ra_tls_ctx.certificate_provider) {
    ra_tls_ctx.certificate_provider =
      std::make_shared<grpc::experimental::StaticDataCertificateProvider>(
        get_identity_key_cert_pairs(ra_tls_get_key_cert()));
  }

  options.set_certificate_provider(ra_tls_ctx.certificate_provider);
  // options.watch_root_certs();
  options.watch_identity_key_cert_pairs();
  options.set_cert_request_type(GRPC_SSL_REQUEST_AND_REQUIRE_CLIENT_CERTIFICATE_BUT_DONT_VERIFY);
  options.set_root_cert_name("");
  options.set_identity_cert_name("");
}

}  // namespace sgx
}  // namespace grpc
