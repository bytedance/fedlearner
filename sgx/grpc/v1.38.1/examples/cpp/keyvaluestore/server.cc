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

#include <grpcpp/grpcpp.h>
#include <grpcpp/security/sgx/sgx_ra_tls.h>

#ifdef BAZEL_BUILD
#include "examples/protos/keyvaluestore.grpc.pb.h"
#else
#include "keyvaluestore.grpc.pb.h"
#endif

#include "../getopt.hpp"

using keyvaluestore::KeyValueStore;
using keyvaluestore::Request;
using keyvaluestore::Response;

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

struct kv_pair {
  const char* key;
  const char* value;
};

static const kv_pair kvs_map[] = {
  {"key1", "value1"}, {"key2", "value2"}, {"key3", "value3"},
  {"key4", "value4"}, {"key5", "value5"},
};

const char* get_value_from_map(const char* key) {
  for (size_t i = 0; i < sizeof(kvs_map) / sizeof(kv_pair); ++i) {
    if (strcmp(key, kvs_map[i].key) == 0) {
      return kvs_map[i].value;
    }
  }
  return "";
}

// Logic and data behind the server's behavior.
class KeyValueStoreServiceImpl final : public KeyValueStore::Service {
  grpc::Status GetValues(grpc::ServerContext* context,
                         grpc::ServerReaderWriter<Response, Request>* stream) override {
    Request request;
    while (stream->Read(&request)) {
      Response response;
      response.set_value(get_value_from_map(request.key().c_str()));
      stream->Write(response);
    }
    return grpc::Status::OK;
  }
};

void RunServer() {
  argparser args;

  KeyValueStoreServiceImpl service;

  grpc::ServerBuilder builder;
  // Listen on the given address without any authentication mechanism.
  std::shared_ptr<grpc::ServerCredentials> creds = nullptr;
  if (args.ssl) {
    creds = std::move(grpc::sgx::TlsServerCredentials(args.config));
  } else {
    creds = std::move(grpc::InsecureServerCredentials());
  }

  builder.AddListeningPort(args.server_address, creds);
  // Register "service" as the instance through which we'll communicate with
  // clients. In this case, it corresponds to an *synchronous* service.
  builder.RegisterService(&service);
  // Finally assemble the server.
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  std::cout << "Server listening on " << args.server_address << std::endl;

  // Wait for the server to shutdown. Note that some other thread must be
  // responsible for shutting down the server for this call to ever return.
  server->Wait();
}

int main(int argc, char** argv) {
  RunServer();

  return 0;
}
