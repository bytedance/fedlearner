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

#include "caching_interceptor.h"
#include "../getopt.hpp"

using keyvaluestore::KeyValueStore;
using keyvaluestore::Request;
using keyvaluestore::Response;

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

class KeyValueStoreClient {
 public:
  KeyValueStoreClient(std::shared_ptr<grpc::Channel> channel)
      : stub_(KeyValueStore::NewStub(channel)) {}

  // Requests each key in the vector and displays the key and its corresponding
  // value as a pair
  void GetValues(const std::vector<std::string>& keys) {
    // Context for the client. It could be used to convey extra information to
    // the server and/or tweak certain RPC behaviors.
    grpc::ClientContext context;
    auto stream = stub_->GetValues(&context);
    for (const auto& key : keys) {
      // Key we are sending to the server.
      Request request;
      request.set_key(key);
      stream->Write(request);

      // Get the value for the sent key
      Response response;
      stream->Read(&response);
      std::cout << key << " : " << response.value() << "\n";
    }
    stream->WritesDone();
    grpc::Status status = stream->Finish();
    if (!status.ok()) {
      std::cout << status.error_code() << ": " << status.error_message()
                << std::endl;
      std::cout << "RPC failed";
    }
  }

 private:
  std::unique_ptr<KeyValueStore::Stub> stub_;
};

void run_client() {
  argparser args;

  std::vector<
      std::unique_ptr<grpc::experimental::ClientInterceptorFactoryInterface>>
      interceptor_creators;
  interceptor_creators.push_back(std::unique_ptr<CachingInterceptorFactory>(
      new CachingInterceptorFactory()));

	std::shared_ptr<grpc::ChannelCredentials> cred = nullptr;
  if (args.ssl) {
    cred = grpc::sgx::TlsCredentials(args.config);
  } else {
    cred = grpc::InsecureChannelCredentials();
  }
  grpc::ChannelArguments c_args;
  std::shared_ptr<grpc::Channel> channel =
    std::move(grpc::experimental::CreateCustomChannelWithInterceptors(
      args.server_address, cred, c_args, std::move(interceptor_creators)));

  KeyValueStoreClient client(channel);

  std::vector<std::string> keys = {"key1", "key2", "key3", "key4",
                                   "key5", "key1", "key2", "key4"};
  client.GetValues(keys);
}

int main(int argc, char** argv) {
  run_client();

  return 0;
}
