# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

# -*- coding: utf-8 -*-

import logging
import unittest
import grpc
import threading
from test.channel import greeter_pb2, greeter_pb2_grpc 

from fedlearner.channel import Bridge

class _Server(greeter_pb2_grpc.GreeterServicer):
    def HelloUnaryUnary(self, request, context):
        return greeter_pb2.Response(
            message="[HelloUnaryUnary]: Hello " + request.name)

    def HelloUnaryStream(self, request, context):
        def response_iterator():
            for i in range (5):
                yield greeter_pb2.Response(
                    message="[HelloUnaryStream]: Hello " + request.name)

        return response_iterator()

    def HelloStreamUnary(self, request_iterator, context):
        response = "[HelloStreamUnary]: Hello"
        for request in request_iterator:
            response += " " + request.name

        return greeter_pb2.Response(message=response)

    def HelloStreamStream(self, request_iterator, context):
        def response_iterator():
            for request in request_iterator:
                yield greeter_pb2.Response(
                    message="[HelloStreamStream]: Hello " + request.name)

        return response_iterator()


class TestBridge(unittest.TestCase):
    def setUp(self):
        super(TestBridge, self).__init__()
        self._token = "test_token"
        self._bridge1 = Bridge("[::]:50001", "localhost:50002",
            token=self._token)
        self._bridge2 = Bridge("[::]:50002", "localhost:50001",
            token=self._token)
        self._bridge1.subscribe(self._bridge_callback("[bridge 1]"))
        self._bridge2.subscribe(self._bridge_callback("[bridge 2]"))

        self._client1 = greeter_pb2_grpc.GreeterStub(self._bridge1)
        self._client2 = greeter_pb2_grpc.GreeterStub(self._bridge2)
        greeter_pb2_grpc.add_GreeterServicer_to_server(
            _Server(), self._bridge1)
        greeter_pb2_grpc.add_GreeterServicer_to_server(
            _Server(), self._bridge2)
        self._bridge1.start()
        self._bridge2.start()

    def _test_run_fn(self, client, name):
        request = greeter_pb2.Request(name=name)

        # unary_unary
        response = client.HelloUnaryUnary(request)
        print(response.message)

        # unary_stream
        response_iterator = \
            client.HelloUnaryStream(request)
        for response in response_iterator:
            print(response.message)
        
        # stream_unary
        def request_iteartor(times):
            for _ in range(times):
                yield request
        response = client.HelloStreamUnary(request_iteartor(5))
        print(response.message)

        # stream_stream
        response_iterator = \
            client.HelloStreamStream(request_iteartor(5))
        for response in response_iterator:
            print(response.message)

    def _bridge_callback(bridge, tag):
        def callback(bridge, event):
            print(tag, ": callback event: ", event.name)
        return callback

    def test_send(self):
        thread1 = threading.Thread(target=self._test_run_fn,
                                   args=(self._client1, "[client 1]",),
                                   daemon=True)
        thread1.start()
        thread2 = threading.Thread(target=self._test_run_fn,
                                   args=(self._client1, "[client 2]",),
                                   daemon=True)
        thread2.start()

        thread1.join()
        thread2.join()
        pass

    def tearDown(self):
        self._bridge1.stop()
        self._bridge2.stop(wait=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(asctime)s: %(message)s in %(pathname)s:%(lineno)d")
    unittest.main()