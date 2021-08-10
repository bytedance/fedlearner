/*
 *
 * Copyright 2015 gRPC authors.
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

#include "getopt.hpp"

#include <grpcpp/grpcpp.h>
#include <grpcpp/security/sgx/grpc_sgx_ra_tls.h>

#ifdef BAZEL_BUILD
#include "examples/protos/helloworld.grpc.pb.h"
#else
#include "helloworld.grpc.pb.h"
#endif

using helloworld::Greeter;
using helloworld::HelloReply;
using helloworld::HelloRequest;

struct argparser {
  bool ssl;
  std::string server_address;
  const char * mr_enclave;
  const char * mr_signer;
  const char * isv_prod_id;
  const char * isv_svn;
  argparser() {
    server_address = getarg("localhost:50051", "-t", "--target");
    ssl = getarg(true, "-ssl", "--ssl");
    mr_enclave = getarg("0", "-mre", "--mr_enclave");
    mr_signer = getarg("0", "-mrs", "--mr_signer");
    isv_prod_id = getarg("0", "-id", "--isv_prod_id");
    isv_svn = getarg("0", "-svn", "--isv_svn");
  };
};

class GreeterClient {
 public:
  GreeterClient(std::shared_ptr<grpc::Channel> channel)
      : stub_(Greeter::NewStub(channel)) {}

  // Assembles the client's payload, sends it and presents the response back
  // from the server.
  std::string SayHello(const std::string& user) {
    // Data we are sending to the server.
    HelloRequest request;
    request.set_name(user);

    // Container for the data we expect from the server.
    HelloReply reply;

    // Context for the client. It could be used to convey extra information to
    // the server and/or tweak certain RPC behaviors.
    grpc::ClientContext context;

    // The actual RPC.
    grpc::Status status = stub_->SayHello(&context, request, &reply);

    // Act upon its status.
    if (status.ok()) {
      return reply.message();
    } else {
      std::cout << status.error_code() << ": " << status.error_message()
                << std::endl;
      return "RPC failed";
    }
  }

 private:
  std::unique_ptr<Greeter::Stub> stub_;
};

void run_client() {
  argparser args;

  std::shared_ptr<grpc::Channel> channel = nullptr;
  if (args.ssl) {
    auto cred = grpc::sgx::TlsCredentials(args.mr_enclave, args.mr_signer, args.isv_prod_id, args.isv_svn);
    channel = std::move(grpc::CreateChannel(args.server_address, cred));
    // channel = std::move(grpc::sgx::CreateSecureChannel(args.server_address, cred));
  } else {
    auto cred = grpc::InsecureChannelCredentials();
    channel = std::move(grpc::CreateChannel(args.server_address, cred));
  }

  GreeterClient greeter(channel);

  std::string user("world");
  std::string reply = greeter.SayHello(user);
  std::cout << "Greeter received: " << reply << std::endl;
};

int main(int argc, char** argv) {
  run_client();

  return 0;
}
