# -*- coding: utf-8 -*-

import logging
import time
import grpc

from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc
from fedlearner.bridge.util import _method_encode, _method_decode

class _UnaryUnaryMultiCallable(grpc.UnaryUnaryMultiCallable):
    def __init__(self, bridge, method, request_serializer,
                 response_deserializer):
        self._bridge = bridge
        self._encoded_method = _method_encode(method)
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self,
                 request,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 wait_for_ready=None,
                 compression=None):
        serialized_request = self._request_serializer(request)
        res = self._bridge._send_unary_unary(
                self._encoded_method,
                bridge_pb2.SendRequest(
                    payload=serialized_request,
                ),
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                compression,
            )

        return self._response_deserializer(res.payload)

    def with_call(self,
                  request,
                  timeout=None,
                  metadata=None,
                  credentials=None,
                  wait_for_ready=None,
                  compression=None):
        pass

    def future(self,
               request,
               timeout=None,
               metadata=None,
               credentials=None,
               wait_for_ready=None,
               compression=None):
        pass

class _UnaryStreamMultiCallable(grpc.UnaryStreamMultiCallable):
    # pylint: disable=too-many-arguments
    def __init__(self, bridge, method, request_serializer,
                 response_deserializer):
        self._bridge = bridge
        self._encoded_method = _method_encode(method)
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(  # pylint: disable=too-many-locals
            self,
            request,
            timeout=None,
            metadata=None,
            credentials=None,
            wait_for_ready=None,
            compression=None):
        serialized_request = self._request_serializer(request)
        res_iter = self._bridge._send_unary_stream(
            self._encoded_method,
            bridge_pb2.SendRequest(
                payload=serialized_request,
            ),
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )
        def r_res_iter():
            for res in res_iter:
                yield self._response_deserializer(res.payload)

        return r_res_iter()

class _StreamUnaryMultiCallable(grpc.StreamUnaryMultiCallable):
    # pylint: disable=too-many-arguments
    def __init__(self, bridge, method, request_serializer,
                 response_deserializer):
        self._bridge = bridge
        self._encoded_method = _method_encode(method)
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self,
                 request_iterator,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 wait_for_ready=None,
                 compression=None):
        def r_req_iter():
            for req in request_iterator:
                yield bridge_pb2.SendRequest(
                    payload=self._request_serializer(req))
        res = self._bridge._send_stream_unary(
            self._encoded_method,
            r_req_iter(),
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        return self._response_deserializer(res.payload)

    def with_call(self,
                  request_iterator,
                  timeout=None,
                  metadata=None,
                  credentials=None,
                  wait_for_ready=None,
                  compression=None):
        return None

    def future(self,
               request_iterator,
               timeout=None,
               metadata=None,
               credentials=None,
               wait_for_ready=None,
               compression=None):
        return None

class _StreamStreamMultiCallable(grpc.StreamStreamMultiCallable):

    def __init__(self, bridge, method, request_serializer,
                 response_deserializer):
        self._bridge = bridge
        self._encoded_method = _method_encode(method)
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self,
                 request_iterator,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 wait_for_ready=None,
                 compression=None):
        def r_req_iter():
            for req in request_iterator:
                yield bridge_pb2.SendRequest(
                    payload=self._request_serializer(req),
                )
        res_iter = self._bridge._send_stream_stream(
            self._encoded_method,
            r_req_iter(),
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )

        def r_res_iter():
            for res in res_iter:
                yield self._response_deserializer(res.payload)

        return r_res_iter()