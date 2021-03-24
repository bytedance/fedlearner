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

# coding: utf-8

import grpc

from fedlearner.channel import channel_pb2


class _MethodHandler(grpc.RpcMethodHandler):
    def __init__(self, method_handler):
        self._method_handler = method_handler
        self._ack = 0

        self.request_streaming = method_handler.request_streaming
        self.response_streaming = method_handler.response_streaming

        self.unary_unary = method_handler.unary_unary
        self.unary_stream = method_handler.unary_stream
        self.stream_unary = method_handler.stream_unary
        self.stream_stream = method_handler.stream_stream

    def request_deserializer(self, serialized_request):
        request = channel_pb2.SendRequest.FromString(serialized_request)
        self._ack = request.seq
        return self._method_handler.request_deserializer(request.payload)

    def response_serializer(self, response):
        return channel_pb2.SendResponse.SerializeToString(
                channel_pb2.SendResponse(
                    code=channel_pb2.Code.OK,
                    ack=self._ack,
                    payload=self._method_handler.response_serializer(response))
            )

class _ResponsedMethodHandler(grpc.RpcMethodHandler):
    def __init__(self, method_handler, response):
        self._method_handler = method_handler
        self._response = response

        self.request_streaming = method_handler.request_streaming
        self.response_streaming = method_handler.response_streaming

    def unary_unary(self, request, context):
        return self._response

    def unary_stream(self, request, context):
        yield self._response

    def stream_unary(self, request_iterator, context):
        return self._response

    def stream_stream(self, request_iterator, context):
        yield self._response

    def request_deserializer(self, serialized_request):
        return channel_pb2.SendRequest.FromString(serialized_request)

    def response_serializer(self, response):
        return channel_pb2.SendResponse.SerializeToString(response)

class ServerInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        self._handlers = set()
        self._peer_identifier = None

    def register_handler(self, handler):
        self._handlers.add(handler)

    def set_peer_identifier(self, peer_identifier):
        self._peer_identifier = peer_identifier

    def _method_match(self, method):
        if not method.startswith('/'):
            return False
        pos = method.find('/', 1)
        if pos < 0:
            return False
        handler = method[1:pos]
        return handler in self._handlers

    def _extract_metadata(self, metadata):
        peer_identifier = None
        for pair in metadata:
            if pair[0] == "fl-channel-id":
                peer_identifier = pair[1]
        return peer_identifier

    def _check_peer_identifier(self, peer_identifier):
        if not self._peer_identifier:
            return False
        return self._peer_identifier == peer_identifier

    def intercept_service(self, continuation, handler_call_details):
        method_handler = continuation(handler_call_details)
        if not self._method_match(handler_call_details.method):
            return method_handler

        peer_identifier = self._extract_metadata(
            handler_call_details.invocation_metadata)

        if not self._check_peer_identifier(peer_identifier):
            return _ResponsedMethodHandler(method_handler,
                        channel_pb2.SendResponse(
                            code=channel_pb2.Code.UNIDENTIFIED
                            ))

        return _MethodHandler(method_handler)
