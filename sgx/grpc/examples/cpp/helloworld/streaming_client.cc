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

#include "caching_interceptor.h"

#ifdef BAZEL_BUILD
#include "examples/protos/helloworld.grpc.pb.h"
#else
#include "helloworld.grpc.pb.h"
#endif

#include "getopt.hpp"
#include "grpc_sgx_ra_tls.h"

using grpc::Channel;
using grpc::ClientContext;
using grpc::Status;
using helloworld::Greeter;
using helloworld::HelloRequest;
using helloworld::HelloReply;


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
		mr_enclave = getarg("0", "-mre", "--mrenclave");
		mr_signer = getarg("0", "-mrs", "--mrsigner");
		isv_prod_id = getarg("0", "-id", "--isv_prod_id");
		isv_svn = getarg("0", "-svn", "--isv_svn");
	};
};

class GreeterClient {
	public:
		GreeterClient(std::shared_ptr<Channel> channel)
      : stub_(Greeter::NewStub(channel)) {}

  // HelloRequests each key in the vector and displays the key and its corresponding
  // value as a pair
  void GetValues(const std::vector<std::string>& keys) {
    // Context for the client. It could be used to convey extra information to
    // the server and/or tweak certain RPC behaviors.
    ClientContext context;
	std::cout << "get value begin" << std::endl;
    auto stream = stub_->GetValues(&context);
	std::cout << "get value end" << std::endl;
    for (const auto& key : keys) {
      // Key we are sending to the server.
      HelloRequest request;
      request.set_name(key);
      stream->Write(request);

      // Get the value for the sent key
      HelloReply response;
      stream->Read(&response);
      std::cout << key << " : " << response.message() << "\n";
    }
    stream->WritesDone();
    Status status = stream->Finish();
    if (!status.ok()) {
      std::cout << status.error_code() << ": " << status.error_message()
                << std::endl;
      std::cout << "RPC failed";
    }
  }

 private:
  std::unique_ptr<Greeter::Stub> stub_;
};

int main(int argc, char** argv) {
  // Instantiate the client. It requires a channel, out of which the actual RPCs
  // are created. This channel models a connection to an endpoint (in this case,
  // localhost at port 50051). We indicate that the channel isn't authenticated
  // (use of InsecureChannelCredentials()).
  // In this example, we are using a cache which has been added in as an
  // interceptor.
	argparser args;
	std::shared_ptr<grpc::ChannelCredentials> creds = nullptr;
	if (args.ssl) {
		creds = grpc::sgx::TlsCredentials(args.mr_enclave, args.mr_signer, args.isv_prod_id, args.isv_svn);
	} else {
		creds = grpc::InsecureChannelCredentials();
	}

  grpc::ChannelArguments cargs;
  std::cout << "connecting"  << std::endl;
  std::vector<
      std::unique_ptr<grpc::experimental::ClientInterceptorFactoryInterface>>
      interceptor_creators;
  interceptor_creators.push_back(std::unique_ptr<CachingInterceptorFactory>(
      new CachingInterceptorFactory()));
  auto channel = grpc::experimental::CreateCustomChannelWithInterceptors(
      args.server_address, creds, cargs, std::move(interceptor_creators));
  std::cout << "channel"  << std::endl;
  GreeterClient client(channel);
  std::vector<std::string> keys = {"key1", "key2", "key3", "key4",
                                   "key5", "key1", "key2", "key4"};
  std::cout << "get values"  << std::endl;
  client.GetValues(keys);

  return 0;
}
