
import grpc

from fedlearner.bridge import bridge_pb2


class StreamStreamAckMethodHandler(grpc.RpcMethodHandler):
    def __init__(self, method_handler):
        self._method_handler = method_handler
        self._ack = 0

        self.request_streaming = self._method_handler.request_streaming
        self.response_streaming = self._method_handler.response_streaming
        self.stream_stream = self._method_handler.stream_stream

    def request_deserializer(self, serialized_request):
        request = bridge_pb2.SendRequest.FromString(serialized_request)
        self._ack = request.seq
        return self._method_handler.request_deserializer(request.payload)

    def response_serializer(self, response):
        return bridge_pb2.SendResponse.SerializeToString(
                bridge_pb2.SendResponse(
                    ack=self._ack,
                    payload=self._method_handler.response_serializer(response))
            )

class AckInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method_handler = continuation(handler_call_details)
        if method_handler.request_streaming \
            and method_handler.response_streaming:
            return StreamStreamAckMethodHandler(method_handler)
        else:
            return method_handler

