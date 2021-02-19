# -*- coding: utf-8 -*-

import collections
from fedlearner import bridge
import logging
import time
import grpc
import threading
import uuid

import fedlearner.bridge.const as const
from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc

class _Client(grpc.Channel):
    def __init__(self, bridge, remote_addr,
        compression=None):
        super(_Client, self).__init__()
        self._bridge = bridge
        self._remote_addr = remote_addr
        self._channel = grpc.insecure_channel(
            self._remote_addr,
            options={
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
                ('grpc.max_reconnect_backoff_ms', 2000)
            },
            compression=compression
        )

        self._client = bridge_pb2_grpc.BridgeStub(self._channel)

    def call(self,
             request,
             timeout=None,
             metadata=None,
             credentials=None,
             wait_for_ready=None,
             compression=None):
        augmented_metadata = self._augment_metadata(metadata)
        return self._client.Call(request,
            metadata = augmented_metadata)

    def subscribe(self, callback, try_to_connect=None):
        self._channel.subscribe(callback, try_to_connect=try_to_connect)

    def unsubscribe(self, callback):
        self._channel.unsubscribe(callback)

    def unary_unary(self,
                    method,
                    request_serializer=None,
                    response_deserializer=None):
        return _UnaryUnaryMultiCallable(
            self, method,
            request_serializer, response_deserializer)

    def unary_stream(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        return _UnaryStreamMultiCallable(
            self, method,
            request_serializer, response_deserializer)

    def stream_unary(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        return _StreamUnaryMultiCallable(
            self, method,
            request_serializer, response_deserializer)

    def stream_stream(self,
                      method,
                      request_serializer=None,
                      response_deserializer=None):
        return _StreamStreamMultiCallable(
            self, method,
            request_serializer, response_deserializer)

    def close(self):
        self._channel.close()

    def _augment_metadata(self, metadata, method=None):
        metadata = list(metadata) if metadata else list()
        if self._bridge._identifier:
            metadata.append(
                (const._grpc_metadata_bridge_id, self._bridge._identifier))
        if self._bridge._peer_identifier:
            metadata.append(
                (const._grpc_metadata_bridge_peer_id, \
                    self._bridge._peer_identifier))
        if self._bridge._token:
            metadata.append(
                (const._grpc_metadata_bridge_token, self._bridge._token))
        if method:
            metadata.append(
                (const._grpc_metadata_bridge_method, method))
        return metadata


    def _grpc_with_retry(self, sender, timeout=None):
        while True:
            self._bridge.wait_for_ready(timeout)
            try:
                return sender()
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    logging.warn("[Bridge] grpc error, status: %s, details: %s", e.code(), e.details())
                    time.sleep(0.5)
                    continue
                raise e

    def _send_unary_unary_with_call(self, method,
        request,
        timeout=None,
        metadata=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendUnaryUnary.with_call(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

    def _send_unary_stream(self, method,
        request,
        timeout=None,
        metadata=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendUnaryStream(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

    def _send_stream_unary_with_call(self, method,
        request_iterator,
        timeout=None,
        metadata=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendStreamUnary.with_call(
                request_iterator,
                timeout,
                augmented_metadata,
            ), timeout)

    def _send_stream_stream(self, method,
        request,
        timeout=None,
        metadata=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendStreamStream(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

class _UnaryUnaryMultiCallable(grpc.UnaryUnaryMultiCallable):
    def __init__(self, client, method, request_serializer,
                 response_deserializer):
        self._client = client
        self._method = method
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self,
                 request,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 wait_for_ready=None,
                 compression=None):
        res, _ = self.with_call(request,
            timeout, metadata, credentials, wait_for_ready, compression)

        return res

    def with_call(self,
                  request,
                  timeout=None,
                  metadata=None,
                  credentials=None,
                  wait_for_ready=None,
                  compression=None):
        serialized_request = self._request_serializer(request)
        bridge_response, rendezvous = self._client._send_unary_unary_with_call(
                self._method,
                bridge_pb2.SendRequest(payload=serialized_request),
                timeout,
                metadata)
        return self._response_deserializer(bridge_response.payload), rendezvous

    def future(self,
               request,
               timeout=None,
               metadata=None,
               credentials=None,
               wait_for_ready=None,
               compression=None):
        raise RuntimeError("cannot use future on bridge")

class _UnaryStreamMultiCallable(grpc.UnaryStreamMultiCallable):

    def __init__(self, client, method,
            request_serializer,
            response_deserializer):
        self._client = client
        self._method = method
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(
            self,
            request,
            timeout=None,
            metadata=None,
            credentials=None,
            wait_for_ready=None,
            compression=None):
        serialized_request = self._request_serializer(request)
        def response_iterator():
            bridge_response_iterator = self._client._send_unary_stream(
                self._method,
                bridge_pb2.SendRequest(payload=serialized_request),
                timeout,
                metadata)
            for res in bridge_response_iterator:
                yield self._response_deserializer(res.payload)

        return response_iterator()

class _StreamUnaryMultiCallable(grpc.StreamUnaryMultiCallable):

    def __init__(self, client, method, request_serializer,
                 response_deserializer):
        self._client = client
        self._method = method
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self,
                 request_iterator,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 wait_for_ready=None,
                 compression=None):
        response, _ = self.with_call(request_iterator, timeout,
            metadata, credentials, wait_for_ready, compression)
        return response

    def with_call(self,
                  request_iterator,
                  timeout=None,
                  metadata=None,
                  credentials=None,
                  wait_for_ready=None,
                  compression=None):

        def bridge_request_iterator():
            for req in request_iterator:
                yield bridge_pb2.SendRequest(
                    payload=self._request_serializer(req))

        bridge_response, rendezvous = self._client._send_stream_unary_with_call(
            self._method,
            bridge_request_iterator(),
            timeout,
            metadata)

        return self._response_deserializer(bridge_response.payload), rendezvous

    def future(self,
               request_iterator,
               timeout=None,
               metadata=None,
               credentials=None,
               wait_for_ready=None,
               compression=None):
        raise RuntimeError("cannot use future on bridge")

class _StreamStreamMultiCallable(grpc.StreamStreamMultiCallable):

    def __init__(self, client, method, request_serializer,
                 response_deserializer):
        self._client = client
        self._method = method
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer

    def __call__(self,
                 request_iterator,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 wait_for_ready=None,
                 compression=None):

        srq = _SendRequestQueue(self._request_serializer, request_iterator)

        def response_iterator():
            while True:
                srq.reset()
                bridge_response_iterator = self._client._send_stream_stream(
                    self._method,
                    iter(srq),
                    timeout,
                    metadata)
                try:
                    for res in bridge_response_iterator:
                        srq.ack(res.ack)
                        yield self._response_deserializer(res.payload)
                    return
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.UNAVAILABLE:
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
                    seq = self._seq,
                    payload=self._request_serializer(
                        next(self._request_iterator))
                )
                self._seq += 1
                self._deque.append(req)
            req = self._deque[self._next]
            self._next += 1

            return req