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
#include <grpc/support/log.h>
#include <grpcpp/security/sgx/sgx_ra_tls.h>

#ifdef BAZEL_BUILD
#include "examples/protos/helloworld.grpc.pb.h"
#else
#include "helloworld.grpc.pb.h"
#endif

#include "../getopt.hpp"

using helloworld::HelloRequest;
using helloworld::HelloReply;
using helloworld::Greeter;

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
        explicit GreeterClient(std::shared_ptr<grpc::Channel> channel)
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

    // The producer-consumer queue we use to communicate asynchronously with the
    // gRPC runtime.
    grpc::CompletionQueue cq;

    // Storage for the status of the RPC upon completion.
    grpc::Status status;

    // stub_->PrepareAsyncSayHello() creates an RPC object, returning
    // an instance to store in "call" but does not actually start the RPC
    // Because we are using the asynchronous API, we need to hold on to
    // the "call" instance in order to get updates on the ongoing RPC.
    std::unique_ptr<grpc::ClientAsyncResponseReader<HelloReply> > rpc(
        stub_->PrepareAsyncSayHello(&context, request, &cq));

    // StartCall initiates the RPC call
    rpc->StartCall();

    // Request that, upon completion of the RPC, "reply" be updated with the
    // server's response; "status" with the indication of whether the operation
    // was successful. Tag the request with the integer 1.
    rpc->Finish(&reply, &status, (void*)1);
    void* got_tag;
    bool ok = false;
    // Block until the next result is available in the completion queue "cq".
    // The return value of Next should always be checked. This return value
    // tells us whether there is any kind of event or the cq_ is shutting down.
    GPR_ASSERT(cq.Next(&got_tag, &ok));

    // Verify that the result from "cq" corresponds, by its tag, our previous
    // request.
    GPR_ASSERT(got_tag == (void*)1);
    // ... and that the request was completed successfully. Note that "ok"
    // corresponds solely to the request for updates introduced by Finish().
    GPR_ASSERT(ok);

    // Act upon the status of the actual RPC.
    if (status.ok()) {
      return reply.message();
    } else {
      std::cout << status.error_code() << ": " << status.error_message()
                << std::endl;
      return "RPC failed";
    }
  }

 private:
  // Out of the passed in Channel comes the stub, stored here, our view of the
  // server's exposed services.
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

  std::cout << "Greeter received: " << user_a << ", " << user_b << std::endl;
}

int main(int argc, char** argv) {
  run_client();

  return 0;
}
