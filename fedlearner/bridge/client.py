# -*- coding: utf-8 -*-

import collections
from fedlearner import bridge
import logging
import time
import grpc
import threading
import uuid

import fedlearner.bridge.const as const
import fedlearner.bridge.util as util
from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc

class _Client(grpc.Channel):
    def __init__(self, bridge, remote_addr,
        compression=None):

        super(_Client, self).__init__()
        self._ready = False
        self._bridge = bridge
        self._remote_addr = remote_addr
        self._compression = compression
        self._channel = grpc.insecure_channel(
            self._remote_addr,
            options={
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
                ('grpc.max_reconnect_backoff_ms', 2000)
            },
            compression=self._compression
        )
        self._lock = threading.RLock()
        self._ready = False
        self._channel_state = None
        self._subscribed_callbacks = list()

        self._client = bridge_pb2_grpc.BridgeStub(self._channel)

    def _subscribe_callback(self, state):
        with self._lock:
            self._channel_state = state
            next_ready = self._ready
            if state == grpc.ChannelConnectivity.IDLE \
                or state == grpc.ChannelConnectivity.CONNECTING \
                or state == grpc.ChannelConnectivity.READY:
                next_ready = True
            elif state == grpc.ChannelConnectivity.TRANSIENT_FAILURE:
                next_ready = False
            elif state == grpc.ChannelConnectivity.SHUTDOWN:
                logging.error("[Bridge] grpc channel state: %s,"
                    " which it cannot recover.", state.name)
                next_ready = False
                # TODO: recreate channel??

            if next_ready == self._ready:
                return

            self._ready = next_ready

            for cb in self._subscribed_callbacks:
                cb(self._ready)

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


    def subscribe(self, callback):
        with self._lock:
            self._subscribed_callbacks.append(callback)
            if len(self._subscribed_callbacks) == 1:
                self._channel.subscribe(self._subscribe_callback,
                    try_to_connect=True)

    def unsubscribe(self, callback):
        with self._lock:
            for index, subscribed_callback in enumerate(
                self._subscribed_callbacks):
                if callback == subscribed_callback:
                    self._subscribed_callbacks.pop(index)
                    if len(self._subscribed_callbacks) == 0:
                        self._channel.unsubscribe(
                            self._subscribe_callback)
                    break

    def close(self):
        self._channel.close()

    def _augment_metadata(self, metadata, method=None):
        if not metadata:
            metadata = list()
        else:
            metadata = list(metadata)

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
                (const._grpc_metadata_bridge_method,
                    util._method_encode(method)))
        return metadata

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

    def _grpc_with_retry(self, sender, timeout=None):
        while True:
            self._bridge.wait_for_ready(timeout)
            try:
                return sender()
            except grpc.RpcError as e:
                logging.warn("[Bridge] grpc error, status: %s, details: %s", e.code(), e.details())
                time.sleep(1)
            except:
                raise

    def _send_unary_unary(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendUnaryUnary(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

    def _send_unary_stream(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendUnaryStream(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

    def _send_stream_unary(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendStreamUnary(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

    def _send_stream_stream(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        augmented_metadata = self._augment_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendStreamStream(
                request,
                timeout,
                augmented_metadata,
            ), timeout)

class _UnaryUnaryMultiCallable(grpc.UnaryUnaryMultiCallable):
    def __init__(self, channel, method, request_serializer,
                 response_deserializer):
        self._channel = channel
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
        serialized_request = self._request_serializer(request)
        res = self._channel._send_unary_unary(
                self._method,
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
    def __init__(self, channel, method, request_serializer,
                 response_deserializer):
        self._channel = channel
        self._method = method
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
        res_iter = self._channel._send_unary_stream(
            self._method,
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
    def __init__(self, channel, method, request_serializer,
                 response_deserializer):
        self._channel = channel
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
        def r_req_iter():
            for req in request_iterator:
                yield bridge_pb2.SendRequest(
                    payload=self._request_serializer(req))
        res = self._channel._send_stream_unary(
            self._method,
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

    def __init__(self, channel, method, request_serializer,
                 response_deserializer):
        self._channel = channel
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

        srq = _SendRequestQueue()

        def req_process():
            try:
                for req in request_iterator:
                    if not srq.append(bridge_pb2.SendRequest(
                        payload=self._request_serializer(req))):
                        # srq closed
                        return
                srq.close()
            except Exception as e:
                srq.close(e)

        threading.Thread(target=req_process, daemon=True).start()

        def response_iterator():
            while True:
                srq.reset()
                resonse_iterator = self._channel._send_stream_stream(
                    self._method,
                    srq,
                    timeout,
                    metadata,
                    credentials,
                    wait_for_ready,
                    compression,
                )
                try:
                    for res in resonse_iterator:
                        srq.ack(res.ack)
                        yield self._response_deserializer(res.payload)
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.UNAVAILABLE:
                        continue
                    srq.close()
                    raise e
                except Exception as e:
                    srq.close()
                    raise e


        return response_iterator()

class _SendRequestQueue():
    def __init__(self):
        self._seq = 0
        self._next = 0
        self._deque = collections.deque()
        self._condition = threading.Condition()
        self._err = None
        self._closed = False

    def append(self, req):
        with self._condition:
            while not self._closed and self._next < len(self._deque):
                self._condition.wait()
            if self._closed:
                return False
            self._seq += 1
            req.seq = self._seq
            self._deque.append(req)
            self._condition.notify_all()
            return True

    def ack(self, ack):
        with self._condition:
            if ack > self._seq:
                return
            n = len(self._deque) - (self._seq - ack)
            if n < 0:
                return
            for _ in range(n):
                self._deque.popleft()
            self._next -= n 

    def close(self, err=None):
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._err = err
            self._condition.notify_all()

    def reset(self):
        with self._condition:
            self._next = 0

    def __len__(self):
        with self._condition:
            return len(self._deque)

    def __iter__(self):
        return self

    def __next__(self):
        with self._condition:
            while not self._closed and self._next >= len(self._deque):
                self._condition.wait()
            if self._closed:
                if self._err:
                    raise self._err
                raise StopIteration()
            req = self._deque[self._next]
            self._next += 1
            if self._next == len(self._deque):
                self._condition.notify_all()
            return req


