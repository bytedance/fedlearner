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

from libcpp.vector cimport vector as cppvector
from libcpp.string cimport string as cppstring

cdef extern from "grpcpp/security/sgx/sgx_ra_tls.h" namespace "grpc::sgx":
  struct sgx_mrs_context:
    pass

cdef extern from "grpcpp/security/sgx/sgx_ra_tls.h" namespace "grpc::sgx":
  cdef void grpc_sgx_ra_tls_verify_init_with_context "grpc::sgx::ra_tls_verify_init"(sgx_mrs_context);

cdef extern from "grpcpp/security/sgx/sgx_ra_tls.h" namespace "grpc::sgx":
  cdef void grpc_sgx_ra_tls_verify_init_with_config "grpc::sgx::ra_tls_verify_init"(const char *);

cdef extern from "grpcpp/security/sgx/sgx_ra_tls.h" namespace "grpc::sgx":
  cdef cppvector[cppstring] grpc_sgx_ra_tls_get_key_cert "grpc::sgx::ra_tls_get_key_cert"()

cdef extern from "grpcpp/security/sgx/sgx_ra_tls.h" namespace "grpc::sgx":
  cdef int grpc_sgx_ra_tls_auth_check_schedule "grpc::sgx::ra_tls_auth_check_schedule"(
    void *, grpc_tls_server_authorization_check_arg *);

cdef class SGXChannelCredentials(ChannelCredentials):
  cdef grpc_tls_identity_pairs *c_pairs

  cdef grpc_tls_certificate_provider *c_provider

  cdef grpc_tls_credentials_options *c_options

  cdef grpc_tls_server_authorization_check_config *c_check_config

  cdef grpc_channel_credentials *c(self) except *
