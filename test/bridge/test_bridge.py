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

from fedlearner.bridge import Bridge

def _request_serializer(request):
    return request.encode('utf8')
def _request_deserializer(request):
    return request.decode('utf8', 'replace')
def _response_serializer(response):
    return response.encode('utf8')
def _response_deserializer(response):
    return response.decode('utf8', 'replace')

class _fake_client():
    def __init__(self, bridge):
        self._unary_unary = bridge.unary_unary(
            '/fake/unary_unary',
            request_serializer=_request_serializer,
            response_deserializer=_response_deserializer,
        )
        self._unary_stream = bridge.unary_stream(
            '/fake/unary_stream',
            request_serializer=_request_serializer,
            response_deserializer=_response_deserializer,
        )
        self._stream_unary = bridge.stream_unary(
            '/fake/stream_unary',
            request_serializer=_request_serializer,
            response_deserializer=_response_deserializer,
        )
        self._stream_stream = bridge.stream_stream(
            '/fake/stream_stream',
            request_serializer=_request_serializer,
            response_deserializer=_response_deserializer,
        )

    def unary_unary(self, request):
        return self._unary_unary(request)

    def unary_stream(self, request):
        return self._unary_stream(request)

    def stream_unary(self, request_iterator):
        return self._stream_unary(request_iterator)

    def stream_stream(self, request_iterator):
        return self._stream_stream(request_iterator)

class _fake_server():
    def __init__(self, bridge):
        rpc_method_handlers = {
            'unary_unary': grpc.unary_unary_rpc_method_handler(
                    self._unary_unary,
                    request_deserializer=_request_deserializer,
                    response_serializer=_response_serializer,
            ),
            'unary_stream': grpc.unary_stream_rpc_method_handler(
                    self._unary_stream,
                    request_deserializer=_request_deserializer,
                    response_serializer=_response_serializer,
            ),
            'stream_unary': grpc.stream_unary_rpc_method_handler(
                    self._stream_unary,
                    request_deserializer=_request_deserializer,
                    response_serializer=_response_serializer,
            ),
            'stream_stream': grpc.stream_stream_rpc_method_handler(
                    self._stream_stream,
                    request_deserializer=_request_deserializer,
                    response_serializer=_response_serializer,
            ),
        }
        generic_handler = grpc.method_handlers_generic_handler(
                'fake', rpc_method_handlers)
        bridge.add_generic_rpc_handlers((generic_handler,))

    def _unary_unary(self, request, context):
        return "[unary_unary]: Hello " + request

    def _unary_stream(self, request, context):
        def response_iterator():
            for i in range (5):
                yield "[unary_stream]: Hello " + request

        return response_iterator()

    def _stream_unary(self, request_iterator, context):
        response = "[stream_unary]: Hello"
        for request in request_iterator:
            response += " " + request

        return response

    def _stream_stream(self, request_iterator, context):
        def response_iterator():
            for request in request_iterator:
                yield "[stream_stream]: Hello" + request

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

        self._client1 = _fake_client(self._bridge1)
        self._client2 = _fake_client(self._bridge2)
        _fake_server(self._bridge1)
        _fake_server(self._bridge2)
        self._bridge1.start()
        self._bridge2.start()

    def _test_run_fn(self, client, request):
        # unary_unary
        print(client.unary_unary(request))

        # unary_stream
        for response in client.unary_stream(request):
            print(response)
        
        # stream_unary
        def request_iteartor(times):
            for _ in range(times):
                yield request
        print(client.stream_unary(request_iteartor(5)))

        # stream_stream
        for response in client.stream_stream(request_iteartor(5)):
            print(response)

    def _bridge_callback(bridge, tag):
        def callback(bridge, event):
            print(tag, ": callback event: ", event.name)
        return callback

    def test_send(self):
        thread1 = threading.Thread(
            target=self._test_run_fn, args=(self._client1, "[client 1]",))
        thread1.start()
        thread2 = threading.Thread(
            target=self._test_run_fn, args=(self._client2, "[client 2]",))
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