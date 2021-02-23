
import collections
import threading
import logging
import time
import grpc

from fedlearner.channel import channel_pb2

class _MethodDetail(
    collections.namedtuple('_MethodDetails',
                          ('method', 'request_serializer',
                          'response_deserializer'))):
    pass

class ClientInterceptor(grpc.UnaryUnaryClientInterceptor,
                         grpc.UnaryStreamClientInterceptor,
                         grpc.StreamUnaryClientInterceptor,
                         grpc.StreamStreamClientInterceptor):
    def __init__(self, retry_interval=1, wait_fn=None):
        assert retry_interval > 0
        self._retry_interval = retry_interval
        self._wait_fn = wait_fn

        self._method_details = dict()

    def register_method(self, method,
                        request_serializer,
                        response_deserializer):
        self._method_details[method] = _MethodDetail(
            method, request_serializer, response_deserializer)

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request)

        request = channel_pb2.SendRequest(
            payload=method_details.request_serializer(request))

        call = _grpc_with_retry(
            lambda: continuation(client_call_details, request),
            self._retry_interval, self._wait_fn)

        return _UnaryOutcome(method_details.response_deserializer, call)

    def intercept_unary_stream(self, continuation, client_call_details,
                               request):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request)

        request = channel_pb2.SendRequest(
            payload=method_details.request_serializer(request))

        stream_response = _grpc_with_retry(
            lambda: continuation(client_call_details, request),
            self._retry_interval, self._wait_fn)

        def response_iterator():
            for response in stream_response:
                yield method_details.response_deserializer(response.payload)

        return response_iterator()

    def intercept_stream_unary(self, continuation, client_call_details,
                               request_iterator):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request_iterator)

        srq = _SingleConsumerSendRequestQueue(
            request_iterator, method_details.request_serializer)
        consumer = srq.consumer()

        call = _grpc_with_retry(
            lambda: continuation(client_call_details, iter(consumer)),
            self._retry_interval, self._wait_fn)

        return _UnaryOutcome(method_details.response_deserializer, call)

    def intercept_stream_stream(self, continuation, client_call_details,
                                request_iterator):
        method_details = self._method_details.get(client_call_details.method)
        if not method_details:
            return continuation(client_call_details, request_iterator)

        srq = _SingleConsumerSendRequestQueue(
            request_iterator, method_details.request_serializer)
        acker = _AckHelper()

        def call():
            consumer = srq.consumer()
            acker.set_consumer(consumer)
            return continuation(client_call_details, iter(consumer))

        def response_iterator(init_stream_response):
            stream_response = init_stream_response
            while True:
                try:
                    for response in stream_response:
                        if acker.ack(response.ack):
                            yield method_details.response_deserializer(
                                response.payload)
                    return
                except grpc.RpcError as e:
                    if _grpc_error_need_recover(e):
                        logging.warning("[channel] grpc error, status: %s"
                            ", details: %s, wait %ds for retry",
                            e.code(), e.details(), self._retry_interval)
                        time.sleep(self._retry_interval)
                        stream_response = _grpc_with_retry(call,
                            self._retry_interval, self._wait_fn)
                        continue
                    raise e

        init_stream_response = _grpc_with_retry(call,
            self._retry_interval, self._wait_fn)

        return response_iterator(init_stream_response)

class _AckHelper():
    def __init__(self):
        self._consumer = None

    def set_consumer(self, consumer):
        self._consumer = consumer

    def ack(self, ack):
        self._consumer.ack(ack)

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

    def __init__(self, request_iterator, request_serializer):
        self._lock = threading.Lock()
        self._seq = 0
        self._offset = 0
        self._deque = collections.deque()
        self._consumer = None

        self._request_lock = threading.Lock()
        self._request_iterator = request_iterator
        self._request_serializer = request_serializer


    def _reset(self):
        #logging.debug("[channel] _SingleConsumerSendRequestQueue reset"
        #    ",self._offset: %d, self._seq: %d, len(self._deque): %d",
        #    self._offset, self._seq, len(self._deque))
        self._offset = 0

    def _empty(self):
        return self._offset == len(self._deque)

    def _get(self):
        assert not self._empty()
        req = self._deque[self._offset]
        self._offset += 1
        #logging.debug("[channel] _SingleConsumerSendRequestQueue get: %d"
        #    ", self._offset: %d, len(self._deque): %d, self._seq: %d",
        #    req.seq, self._offset, len(self._deque), self._seq)
        return req

    def _add(self, raw_req):
        req = channel_pb2.SendRequest(
            seq=self._seq,
            payload=self._request_serializer(raw_req))
        self._seq += 1
        self._deque.append(req)

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
            n = self._seq - ack
            while len(self._deque) >= n:
                self._deque.popleft()
                self._offset -= 1
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
                with self._lock:
                    # check again
                    self._consumer_check_or_call(consumer, stop_iteration_fn)
                    if not self._empty():
                        self._request_lock.release()
                        return self._get()
                # call next maybe block by user code
                # then return data or raise StopIteration()
                # so use self._request_lock instead of self._lock
                raw_req = next(self._request_iterator)
                with self._lock:
                    self._add(raw_req)

                self._request_lock.release()

    def consumer(self):
        with self._lock:
            self._reset()
            self._consumer = _SingleConsumerSendRequestQueue.Consumer(self)
            return self._consumer

def _grpc_with_retry(call, interval=1, wait_fn=None):
    while True:
        try:
            if wait_fn:
                wait_fn()
            result = call()
            if not result.running() and result.exception() is not None:
                raise result.exception()
            return result
        except grpc.RpcError as e:
            if _grpc_error_need_recover(e):
                logging.warning("[channel] grpc error, status: %s"
                    ", details: %s, wait %ds for retry",
                    e.code(), e.details(), interval)
                time.sleep(interval)
                continue
            raise e

def _grpc_error_need_recover(e):
    if e.code() in (grpc.StatusCode.UNAVAILABLE,
                    grpc.StatusCode.INTERNAL):
        return True
    if e.code() == grpc.StatusCode.UNKNOWN:
        httpstatus = _grpc_error_get_http_status(e.details())
        # catch all header with non-200 OK
        if httpstatus:
            #if 400 <= httpstatus < 500:
            #    return True
            return True
    return False

def _grpc_error_get_http_status(details):
    try:
        if details.count("http2 header with status") > 0:
            fields = details.split(":")
            if len(fields) == 2:
                return int(details.split(":")[1])
    except Exception as e: #pylint: disable=broad-except
        logging.warning(
            "[channel] grpc_error_get_http_status except: %s, details: %s",
            repr(e), details)
    return None

class _UnaryOutcome(grpc.Call, grpc.Future):

    def __init__(self, response_deserializer, call):
        super(_UnaryOutcome, self).__init__()
        self._response_deserializer = response_deserializer
        self._response = None
        self._call = call

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
