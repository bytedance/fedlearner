
import grpc

from fedlearner.channel import channel_pb2


class _MethodHandler(grpc.RpcMethodHandler):
    def __init__(self, method_handler):
        self._method_handler = method_handler
        self._ack = 0

        self.request_streaming = self._method_handler.request_streaming
        self.response_streaming = self._method_handler.response_streaming
        self.unary_unary = self._method_handler.unary_unary
        self.unary_stream = self._method_handler.unary_stream
        self.stream_unary = self._method_handler.stream_unary
        self.stream_stream = self._method_handler.stream_stream

    def request_deserializer(self, serialized_request):
        request = channel_pb2.SendRequest.FromString(serialized_request)
        self._ack = request.seq
        return self._method_handler.request_deserializer(request.payload)

    def response_serializer(self, response):
        return channel_pb2.SendResponse.SerializeToString(
                channel_pb2.SendResponse(
                    ack=self._ack,
                    payload=self._method_handler.response_serializer(response))
            )

class ServerInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        self._handlers = set()

    def register_handler(self, handler):
        self._handlers.add(handler)

    def _method_match(self, method):
        if not method.startswith('/'):
            return False
        pos = method.find('/', 1)
        if pos < 0:
            return False
        handler = method[1:pos]
        return handler in self._handlers

    def intercept_service(self, continuation, handler_call_details):
        method_handler = continuation(handler_call_details)
        if self._method_match(handler_call_details.method):
            return _MethodHandler(method_handler)
        return method_handler
