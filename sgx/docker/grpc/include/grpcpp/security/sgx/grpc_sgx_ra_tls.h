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

#ifndef GRPC_SGX_RA_TLS_H
#define GRPC_SGX_RA_TLS_H

#include <memory>

#include <grpcpp/security/credentials.h>
#include <grpcpp/security/server_credentials.h>

namespace grpc {
namespace sgx {

void parse_args(const char * mr_enclave, const char * mr_signer,
                const char * isv_prod_id, const char * isv_svn);

void ra_tls_verify_init(bool in_enclave);

int server_auth_check_schedule(void* /* config_user_data */,
                               grpc_tls_server_authorization_check_arg* arg);

std::shared_ptr<grpc::ChannelCredentials> TlsCredentials(
    const char* mr_enclave, const char* mr_signer,
    const char* isv_prod_id, const char* isv_svn);

std::shared_ptr<grpc::Channel> CreateSecureChannel(
    string target_str, std::shared_ptr<grpc::ChannelCredentials> channel_creds);

std::vector<std::string> get_server_key_cert();

std::shared_ptr<grpc::ServerCredentials> TlsServerCredentials();

}  // namespace sgx
}  // namespace grpc

#endif  // GRPC_SGX_RA_TLS_H
