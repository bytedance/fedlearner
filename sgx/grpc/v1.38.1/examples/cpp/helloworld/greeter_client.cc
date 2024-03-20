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

#include <grpcpp/grpcpp.h>
#include <grpcpp/security/sgx/sgx_ra_tls.h>

#ifdef BAZEL_BUILD
#include "examples/protos/helloworld.grpc.pb.h"
#else
#include "helloworld.grpc.pb.h"
#endif

#include "../getopt.hpp"

using helloworld::Greeter;
using helloworld::HelloReply;
using helloworld::HelloRequest;

struct argparser {
  bool ssl;
  const char* config;
  std::string server_address;
  argparser() {
    server_address = getarg("localhost:50051", "-t", "--target");
    ssl = getarg(true, "-ssl", "--ssl");
    config = getarg("dynamic_config.json", "-cfg", "--config");
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
    auto cred = grpc::sgx::TlsCredentials(args.config);
    channel = std::move(grpc::CreateChannel(args.server_address, cred));
    // channel = std::move(grpc::sgx::CreateSecureChannel(args.server_address, cred));
  } else {
    auto cred = grpc::InsecureChannelCredentials();
    channel = std::move(grpc::CreateChannel(args.server_address, cred));
  }

  GreeterClient greeter(channel);

  std::string user_a = greeter.SayHello("a");
  std::string user_b = greeter.SayHello("b");

  std::cout << "Greeter received: " << user_a << ", "<< user_b << std::endl;
};

int main(int argc, char** argv) {
  run_client();

  return 0;
}
