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

#include <grpcpp/grpcpp.h>
#include <grpcpp/security/credentials.h>
#include <grpcpp/security/server_credentials.h>

typedef struct ::grpc_impl::experimental::TlsCredentialReloadInterface
    TlsCredentialReloadInterface;
typedef class ::grpc_impl::experimental::TlsCredentialReloadArg
    TlsCredentialReloadArg;

namespace grpc {
namespace sgx {

std::shared_ptr<grpc::ChannelCredentials> TlsCredentials(
    const char* mrenclave, const char* mrsigner,
    const char* isv_prod_id, const char* isv_svn);

std::shared_ptr<grpc::Channel> CreateSecureChannel(string, std::shared_ptr<grpc::ChannelCredentials>);

std::shared_ptr<grpc::ServerCredentials> SslServerCredentials();

class TestTlsCredentialReload : public TlsCredentialReloadInterface {
	int Schedule(TlsCredentialReloadArg* arg) override {
		//GPR_ASSERT(arg != nullptr);
		//struct TlsKeyMaterialsConfig::PemKeyCertPair pair3 = {"private_key3",
		//	"cert_chain3"};
		//arg->set_pem_root_certs("new_pem_root_certs");
		//arg->add_pem_key_cert_pair(pair3);
		//arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_NEW);
		return 0;
	}

	void Cancel(TlsCredentialReloadArg* arg) override {
		GPR_ASSERT(arg != nullptr);
		arg->set_status(GRPC_SSL_CERTIFICATE_CONFIG_RELOAD_FAIL);
		arg->set_error_details("cancelled");
	}
};

}  // namespace sgx
}  // namespace grpc

#endif  // GRPC_SGX_RA_TLS_H
