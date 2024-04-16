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
#include <grpcpp/ext/proto_server_reflection_plugin.h>

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
    server_address = getarg("0.0.0.0:50051", "-host", "--host");
    ssl = getarg(true, "-ssl", "--ssl");
    config = getarg("dynamic_config.json", "-cfg", "--config");
  };
};

// Logic and data behind the server's behavior.
class GreeterServiceImpl final : public Greeter::Service {
  grpc::Status SayHello(
    grpc::ServerContext* context, const HelloRequest* request, HelloReply* reply) override {
    std::string prefix("Hello ");
    reply->set_message(prefix + request->name());
    return grpc::Status::OK;
  }
};

void RunServer() {
  argparser args;

  GreeterServiceImpl service;

  grpc::EnableDefaultHealthCheckService(true);
  grpc::reflection::InitProtoReflectionServerBuilderPlugin();

  grpc::ServerBuilder builder;
  std::shared_ptr<grpc::ServerCredentials> creds = nullptr;

  if (args.ssl) {
    creds = std::move(grpc::sgx::TlsServerCredentials(args.config));
  } else {
    creds = std::move(grpc::InsecureServerCredentials());
  }

  GPR_ASSERT(creds.get() != nullptr);

  // Listen on the given address.
  builder.AddListeningPort(args.server_address, creds);

  // Register "service" as the instance through which we'll communicate with
  // clients. In this case it corresponds to an *synchronous* service.
  builder.RegisterService(&service);
  // Finally assemble the server.
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  std::cout << "SSL enable: " << args.ssl << ", Server listening on " << args.server_address << std::endl;

  // Wait for the server to shutdown. Note that some other thread must be
  // responsible for shutting down the server for this call to ever return.
  server->Wait();
}

int main(int argc, char** argv) {
  RunServer();

  return 0;
}
