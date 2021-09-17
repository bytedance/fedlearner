/*
 *
 * Copyright 2018 gRPC authors.
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

#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include <grpcpp/grpcpp.h>

#ifdef BAZEL_BUILD
#include "examples/protos/helloworld.grpc.pb.h"
#else
#include "helloworld.grpc.pb.h"
#endif

#include "getopt.hpp"
#include "grpc_sgx_ra_tls.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::ServerReaderWriter;
using grpc::Status;
using helloworld::Greeter;
using helloworld::HelloRequest;
using helloworld::HelloReply;

struct kv_pair {
  const char* name;
  const char* message;
};

static const kv_pair kvs_map[] = {
    {"key1", "value1"}, {"key2", "value2"}, {"key3", "value3"},
    {"key4", "value4"}, {"key5", "value5"},
};

const char* get_value_from_map(const char* key) {
  for (size_t i = 0; i < sizeof(kvs_map) / sizeof(kv_pair); ++i) {
    if (strcmp(key, kvs_map[i].name) == 0) {
      return kvs_map[i].message;
    }
  }
  return "";
}

// Logic and data behind the server's behavior.
class GreeterServiceImpl final : public Greeter::Service {
  Status GetValues(ServerContext* context,
                   ServerReaderWriter<HelloReply, HelloRequest>* stream) override {
    HelloRequest request;
    while (stream->Read(&request)) {
      HelloReply response;
	  std::cout << "reading " << request.name() << std::endl;
      response.set_message(get_value_from_map(request.name().c_str()));
      stream->Write(response);
    }
    return Status::OK;
  }
};

struct argparser {
	bool ssl;
	std::string server_address;
	argparser() {
		ssl = getarg(true, "-ssl", "--ssl");
		server_address = getarg("0.0.0.0:50051", "-host", "--host");
	};
};

void RunServer() {
  GreeterServiceImpl service;

  argparser args;
  ServerBuilder builder;
  // Listen on the given address without any authentication mechanism.
  std::shared_ptr<grpc::ServerCredentials> creds = nullptr;
  if (args.ssl) {
	  creds = std::move(grpc::sgx::TlsServerCredentials());
  } else {
	  creds = std::move(grpc::InsecureServerCredentials());
  }

  builder.AddListeningPort(args.server_address, creds);
  // Register "service" as the instance through which we'll communicate with
  // clients. In this case, it corresponds to an *synchronous* service.
  builder.RegisterService(&service);
  // Finally assemble the server.
  std::unique_ptr<Server> server(builder.BuildAndStart());
  std::cout << "Server listening on " << args.server_address << std::endl;

  // Wait for the server to shutdown. Note that some other thread must be
  // responsible for shutting down the server for this call to ever return.
  server->Wait();
}

int main(int argc, char** argv) {
  RunServer();

  return 0;
}
