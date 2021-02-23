
import collections
import threading
import logging
import time
import grpc

from fedlearner.bridge import bridge_pb2

class _MethodDetail(
    collections.namedtuple('_MethodDetails',
                          ('method', 'request_serializer',
                          'response_deserializer'))):
    pass

class WaitInterceptor(grpc.UnaryUnaryClientInterceptor,
                       grpc.UnaryStreamClientInterceptor,
                       grpc.StreamUnaryClientInterceptor,
                       grpc.StreamStreamClientInterceptor):
    def __init__(self, wait):
        self._methods = set()
        self._wait = wait

    def register_method(self, method):
        self._methods.add(method)

    def _handle(self, continuation, client_call_details, request):
        if client_call_details.method in self._methods:
            self._wait(client_call_details.timeout)
        return continuation(client_call_details, request)

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        return self._handle(continuation, client_call_details, request)

    def intercept_unary_stream(self, continuation, client_call_details,
                               request):
        return self._handle(continuation, client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details,
                               request_iterator):
        return self._handle(continuation, client_call_details, request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details,
                                request_iterator):
        return self._handle(continuation, client_call_details, request_iterator)

def stream_stream_request_serializer(request):
    return bridge_pb2.SendRequest.SerializeToString(request)

def stream_stream_response_deserializer(serialized_response):
    return bridge_pb2.SendResponse.FromString(serialized_response)

class RetryInterceptor(grpc.UnaryUnaryClientInterceptor,
                       grpc.UnaryStreamClientInterceptor,
                       grpc.StreamUnaryClientInterceptor,
                       grpc.StreamStreamClientInterceptor):
    def __init__(self, retry_interval):
        assert retry_interval > 0
        self._retry_interval = retry_interval
        self._method_details = dict()

    def register_method(self, method,
                        request_serializer,
                        response_deserializer):
        self._method_details[method] = _MethodDetail(
            method, request_serializer, response_deserializer)

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        method_details = self._method_details.get(client_call_details.method)
        if method_details:
            return _grpc_with_retry(
                lambda: continuation(client_call_details, request),
                self._retry_interval)

        return continuation(client_call_details, request)


    def intercept_unary_stream(self, continuation, client_call_details,
                               request):
        method_details = self._method_details.get(client_call_details.method)
        if method_details:
            return _grpc_with_retry(
                lambda: continuation(client_call_details, request),
                self._retry_interval)

        return continuation(client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details,
                               request_iterator):
        method_details = self._method_details.get(client_call_details.method)
        if method_details:
            return _grpc_with_retry(
                lambda: continuation(client_call_details, request_iterator),
                self._retry_interval)

        return continuation(client_call_details, request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details,
                                request_iterator):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request_iterator)

        srq = _SendRequestQueue(
            method_details.request_serializer, request_iterator)

        bridge_response_iterator = _grpc_with_retry(
            lambda: continuation(client_call_details, iter(srq)),
            self._retry_interval)

        def response_iterator():
            nonlocal bridge_response_iterator
            while True:
                try:
                    for res in bridge_response_iterator:
                        srq.ack(res.ack)
                        yield method_details.response_deserializer(res.payload)
                    return
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.UNAVAILABLE:
                        srq.reset()
                        bridge_response_iterator = _grpc_with_retry(
                            lambda: continuation(
                                client_call_details, iter(srq)),
                            self._retry_interval)
                        continue
                    raise e

        return response_iterator()

class _SendRequestQueue():
    def __init__(self, request_serializer, request_iterator):
        self._seq = 0
        self._next = 0
        self._lock = threading.Lock()
        self._deque = collections.deque()
        self._request_serializer = request_serializer
        self._request_iterator = request_iterator

    def ack(self, ack):
        with self._lock:
            if ack >= self._seq:
                return
            n = self._seq - ack
            while len(self._deque) >= n:
                self._deque.popleft()
                self._next -= 1

    def reset(self):
        with self._lock:
            self._next = 0

    def __iter__(self):
        return self

    def __next__(self):
        with self._lock:
            if self._next == len(self._deque):
                req = bridge_pb2.SendRequest(
                    seq=self._seq,
                    payload=self._request_serializer(
                        next(self._request_iterator))
                )
                self._seq += 1
                self._deque.append(req)
            req = self._deque[self._next]
            self._next += 1

            return req

def _grpc_with_retry(handle, interval=1):
    while True:
        try:
            res = handle()
            if type(res) == grpc.RpcError: #pylint: disable=unidiomatic-typecheck
                raise res
            return res
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                logging.warning("[Bridge] grpc error, status: %s"
                    ", details: %s, wait %ds for retry",
                    e.code(), e.details(), interval)
                time.sleep(interval)
                continue
            raise e
