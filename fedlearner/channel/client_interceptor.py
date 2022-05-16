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
# pylint: disable=broad-except

import collections
import threading
import time
import grpc

from fedlearner.common import fl_logging, stats
from fedlearner.channel import channel_pb2

class _MethodDetail(
    collections.namedtuple('_MethodDetails',
                          ('method', 'request_serializer',
                          'response_deserializer'))):
    pass


class _ClientCallDetails(
        collections.namedtuple('_ClientCallDetails',
                               ('method', 'timeout', 'metadata', 'credentials',
                                'wait_for_ready', 'compression')),
        grpc.ClientCallDetails):
    pass


class ClientInterceptor(grpc.UnaryUnaryClientInterceptor,
                         grpc.UnaryStreamClientInterceptor,
                         grpc.StreamUnaryClientInterceptor,
                         grpc.StreamStreamClientInterceptor):
    def __init__(self,
                 identifier,
                 retry_interval,
                 wait_fn=None,
                 check_fn=None,
                 stats_client=None):
        self._retry_interval = retry_interval
        self._identifer = identifier
        self._wait_fn = wait_fn
        self._check_fn = check_fn

        self._method_details = dict()

        self._fl_metadata = ("fl-channel-id", self._identifer)
        self._stats_client = stats_client or stats.NoneClient()

    def _wait(self):
        if self._wait_fn:
            self._wait_fn()

    def _check(self):
        if self._check_fn:
            self._check_fn()

    def _error(self, error):
        self._error_fn(error)

    def register_method(self, method,
                        request_serializer,
                        response_deserializer):
        self._method_details[method] = _MethodDetail(
            method, request_serializer, response_deserializer)

    def _augment_metadata(self, metadata):
        base_metadata = tuple(metadata) if metadata else ()
        return (base_metadata + self._fl_metadata,)

    def _merge_client_call_details(self, client_call_details):
        augmented_metadata = self._augment_metadata(
            client_call_details.metadata)
        return _ClientCallDetails(
            client_call_details.method, client_call_details.timeout,
            augmented_metadata, None, None, None)

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request)

        client_call_details = self._merge_client_call_details(
            client_call_details)

        request = channel_pb2.SendRequest(
            payload=method_details.request_serializer(request))

        def call():
            self._wait()
            return continuation(client_call_details, request)

        with self._stats_client.timer("channel.client.unary_unary_timing",
            tags={"grpc_method": method_details.method}):
            _call = _grpc_with_retry(call, self._retry_interval)
            return _UnaryOutcome(
                method_details.response_deserializer, _call, self._check_fn)

    def intercept_unary_stream(self, continuation, client_call_details,
                               request):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request)

        client_call_details = self._merge_client_call_details(
            client_call_details)

        request = channel_pb2.SendRequest(
            payload=method_details.request_serializer(request))

        def call():
            self._wait()
            return continuation(client_call_details, request)

        timer = self._stats_client.timer(
                "channel.client.unary_stream_timing",
                tags={"grpc_method": method_details.method}
            ).start()

        stream_response = _grpc_with_retry(call, self._retry_interval)

        def response_iterator():
            for response in stream_response:
                self._check_fn(response)
                yield method_details.response_deserializer(response.payload)
            timer.stop()

        return response_iterator()

    def intercept_stream_unary(self, continuation, client_call_details,
                               request_iterator):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request_iterator)

        client_call_details = self._merge_client_call_details(
            client_call_details)

        srq = _SingleConsumerSendRequestQueue(
            request_iterator, method_details.request_serializer)

        def call():
            self._wait()
            consumer = srq.consumer()
            return continuation(client_call_details, iter(consumer))

        with self._stats_client.timer("channel.client.stream_unary_timing",
            tags={"grpc_method": method_details.method}):
            _call = _grpc_with_retry(call, self._retry_interval)
            return _UnaryOutcome(method_details.response_deserializer,
                _call, self._check_fn)

    def intercept_stream_stream(self, continuation, client_call_details,
                                request_iterator):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request_iterator)

        client_call_details = self._merge_client_call_details(
            client_call_details)

        srq = _SingleConsumerSendRequestQueue(
            request_iterator, method_details.request_serializer,
            stats_client=self._stats_client.with_tags(
                tags={"grpc_method": method_details.method}
            ),
            stats_prefix="channel.client.stream_stream")
        consumer = None

        def call():
            nonlocal consumer
            self._wait()
            consumer = srq.consumer()
            return continuation(client_call_details, iter(consumer))

        def response_iterator(init_stream_response):
            stream_response = init_stream_response
            while True:
                try:
                    for response in stream_response:
                        self._check_fn(response)
                        if consumer.ack(response.ack):
                            yield method_details.response_deserializer(
                                response.payload)
                    return
                except grpc.RpcError as e:
                    if _grpc_error_need_recover(e):
                        fl_logging.warning("[Channel] grpc error, status: %s, "
                            "details: %s, wait %ds for retry",
                            e.code(), e.details(), self._retry_interval)
                        time.sleep(self._retry_interval)
                        stream_response = _grpc_with_retry(call,
                            self._retry_interval)
                        continue
                    raise e

        init_stream_response = _grpc_with_retry(call, self._retry_interval)

        return response_iterator(init_stream_response)


class _SingleConsumerSendRequestQueue():
    class Consumer():
        def __init__(self, queue):
            self._queue = queue

        def ack(self, ack):
            return self._queue.ack(self, ack)

        def __iter__(self):
            return self

        def __next__(self):
            return self._queue.next(self)

        next = __next__

    def __init__(self, request_iterator, request_serializer,
                 stats_client=None, stats_prefix=""):
        self._lock = threading.Lock()
        self._seq = 0
        self._offset = 0
        self._deque = collections.deque()
        self._consumer = None

        self._request_lock = threading.Lock()
        self._request_iterator = request_iterator
        self._request_serializer = request_serializer
        self._stats_client = stats_client or stats.NoneClient()
        self._stats_prefix = stats_prefix

    def _reset(self):
        if self._offset > 0:
            self._stats_client.incr(
                "%s_resend"%self._stats_prefix, self._offset)
        self._offset = 0

    def _empty(self):
        return self._offset == len(self._deque)

    def _get(self):
        assert not self._empty()
        req = self._deque[self._offset]
        req.ts = time.time()
        self._offset += 1
        return req.req

    def _add(self, raw_req):
        class _Request():
            def __init__(self, req, ts):
                self.req = req
                self.ts = ts

        req = channel_pb2.SendRequest(
            seq=self._seq,
            payload=self._request_serializer(raw_req))
        self._seq += 1
        self._deque.append(_Request(req, time.time()))

    def _consumer_check(self, consumer):
        return self._consumer == consumer

    def _consumer_check_or_call(self, consumer, call):
        if not self._consumer_check(consumer):
            call()

    def ack(self, consumer, ack):
        with self._lock:
            if not self._consumer_check(consumer):
                return False
            if ack >= self._seq:
                return False
            now = time.time()
            n = self._seq - ack
            with self._stats_client.pipeline() as pipe:
                while len(self._deque) >= n:
                    req = self._deque.popleft()
                    self._offset -= 1
                    pipe.timing("%s_timing"%self._stats_prefix,
                        (now-req.ts)*1000)
            return True

    def next(self, consumer):
        def stop_iteration_fn():
            raise StopIteration()
        while True:
            with self._lock:
                self._consumer_check_or_call(consumer, stop_iteration_fn)
                if not self._empty():
                    return self._get()

            # get from request_iterator
            if self._request_lock.acquire(timeout=1):
                try:
                    with self._lock:
                        # check again
                        self._consumer_check_or_call(
                            consumer, stop_iteration_fn)
                        if not self._empty():
                            return self._get()
                    # call next maybe block in user code
                    # then return data or raise StopIteration()
                    # so use self._request_lock instead of self._lock
                    raw_req = next(self._request_iterator)
                    with self._lock:
                        self._add(raw_req)
                finally:
                    self._request_lock.release()

    def consumer(self):
        with self._lock:
            self._reset()
            self._consumer = _SingleConsumerSendRequestQueue.Consumer(self)
            return self._consumer


def _grpc_with_retry(call, interval=1):
    while True:
        try:
            result = call()
            if not result.running() and result.exception() is not None:
                raise result.exception()
            return result
        except grpc.RpcError as e:
            if _grpc_error_need_recover(e):
                fl_logging.warning("[Channel] grpc error, status: %s, "
                    "details: %s, wait %ds for retry",
                    e.code(), e.details(), interval)
                time.sleep(interval)
                continue
            raise e

def _grpc_error_need_recover(e):
    if e.code() in (grpc.StatusCode.UNAVAILABLE,
                    grpc.StatusCode.INTERNAL,
                    grpc.StatusCode.UNIMPLEMENTED):
        return True
    if e.code() == grpc.StatusCode.UNKNOWN:
        httpstatus = _grpc_error_get_http_status(e.details())
        # catch all header with non-200 OK
        if httpstatus:
            #if 400 <= httpstatus < 500:
            #    return True
            return True
    return True # recover in any case
    #return False

def _grpc_error_get_http_status(details):
    try:
        if details.count("http2 header with status") > 0:
            fields = details.split(":")
            if len(fields) == 2:
                return int(details.split(":")[1])
    except Exception as e:
        fl_logging.warning(
            "[Channel] grpc_error_get_http_status except: %s, details: %s",
            repr(e), details)
    return None


class _UnaryOutcome(grpc.Call, grpc.Future):

    def __init__(self, response_deserializer, call, check_fn):
        super(_UnaryOutcome, self).__init__()
        self._response_deserializer = response_deserializer
        self._response = None
        self._call = call
        self._check_fn = check_fn

    def initial_metadata(self):
        return self._call.initial_metadata()

    def trailing_metadata(self):
        return self._call.trailing_metadata()

    def code(self):
        return self._call.code()

    def details(self):
        return self._call.details()

    def is_active(self):
        return self._call.is_active()

    def time_remaining(self):
        return self._call.time_remaining()

    def cancel(self):
        return self._call.cancel()

    def add_callback(self, callback):
        return self._call.add_callback(callback)

    def cancelled(self):
        return False

    def running(self):
        return False

    def done(self):
        return True

    def result(self, ignored_timeout=None):
        if self._response:
            return self._response
        response = self._call.result(ignored_timeout)
        self._check_fn(response)
        self._response = self._response_deserializer(response.payload)
        return self._response

    def exception(self, ignored_timeout=None):
        return None

    def traceback(self, ignored_timeout=None):
        return None

    def add_done_callback(self, fn):
        def callback(_):
            fn(self)
        self._call.add_done_callback(callback)


# TODO _StreamOutcome():
