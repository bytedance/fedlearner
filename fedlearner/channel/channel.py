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

import time
import uuid
import threading
import enum
from concurrent import futures

import grpc
from fedlearner.common import fl_logging, stats, common
from fedlearner.channel import channel_pb2, channel_pb2_grpc
from fedlearner.proxy.channel import make_insecure_channel, \
    make_secure_channel, ChannelType
from fedlearner.channel.client_interceptor import ClientInterceptor
from fedlearner.channel.server_interceptor import ServerInterceptor


class ChannelError(Exception):
    pass


class Channel():
    class State(enum.Enum):
        IDLE = 0
        CONNECTING_UNCONNECTED = 1
        CONNECTED_UNCONNECTED = 2
        CONNECTING_CONNECTED = 3
        READY = 4
        CONNECTED_CLOSED = 5
        CLOSING_CONNECTED = 6
        CLOSING_CLOSED = 7
        CLOSED_CONNECTED = 8
        DONE = 9
        ERROR = 10

    class Event(enum.Enum):
        CONNECTED = 0
        CLOSING = 1
        CLOSED = 2
        PEER_CONNECTED = 3
        PEER_CLOSED = 4
        ERROR = 5

    _next_table = {
        State.IDLE: {},
        State.CONNECTING_UNCONNECTED: {
            Event.CONNECTED: State.CONNECTED_UNCONNECTED,
            Event.PEER_CONNECTED: State.CONNECTING_CONNECTED,
            Event.ERROR: State.ERROR,
        },
        State.CONNECTED_UNCONNECTED: {
            Event.PEER_CONNECTED: State.READY,
            Event.ERROR: State.ERROR,
        },
        State.CONNECTING_CONNECTED: {
            Event.CONNECTED: State.READY,
            Event.ERROR: State.ERROR,
        },
        State.READY: {
            Event.CLOSING: State.CLOSING_CONNECTED,
            Event.PEER_CLOSED: State.CONNECTED_CLOSED,
            Event.ERROR: State.ERROR,
        },
        State.CONNECTED_CLOSED: {
            Event.CLOSING: State.CLOSING_CLOSED,
            Event.CLOSED: State.DONE,
            Event.ERROR: State.ERROR,
        },
        State.CLOSING_CONNECTED: {
            Event.CLOSED: State.CLOSED_CONNECTED,
            Event.PEER_CLOSED: State.CLOSING_CLOSED,
            Event.ERROR: State.ERROR,
        },
        State.CLOSING_CLOSED: {
            Event.CLOSED: State.DONE,
            Event.ERROR: State.ERROR,
        },
        State.CLOSED_CONNECTED: {
            Event.PEER_CLOSED :State.DONE,
            Event.ERROR: State.ERROR,
        },
        State.DONE: {},
        State.ERROR: {},
    }

    _CONNECTING_STATES = set([
        State.CONNECTING_UNCONNECTED,
        State.CONNECTING_CONNECTED,
    ])

    _CONNECTED_STATES = set([
        State.CONNECTED_UNCONNECTED,
        State.READY,
    ])

    _CLOSING_STATES = set([
        State.CLOSING_CONNECTED,
        State.CLOSING_CLOSED,
    ])

    _CLOSED_STATES = set([
        State.CLOSED_CONNECTED
    ])

    _PEER_UNCONNECTED_STATES = set([
        State.CONNECTING_UNCONNECTED,
        State.CONNECTED_UNCONNECTED,
    ])

    _PEER_CLOSED_STATES = set([
        State.CONNECTED_CLOSED,
        State.CLOSING_CLOSED,
    ])

    def __init__(self,
                 listen_address,
                 remote_address,
                 token=None,
                 max_workers=2,
                 compression=grpc.Compression.Gzip,
                 heartbeat_timeout=120,
                 retry_interval=2,
                 stats_client=None):
        # identifier
        self._identifier = uuid.uuid4().hex[:16]
        self._peer_identifier = ""
        self._token = token if token else ""

        # lock & condition
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        # heartbeat
        if heartbeat_timeout <= 0:
            raise ValueError("[Channel] heartbeat_timeout must be positive")
        self._heartbeat_timeout = heartbeat_timeout
        self._heartbeat_interval = self._heartbeat_timeout / 6
        self._next_heartbeat_at = 0
        self._heartbeat_timeout_at = 0
        self._peer_heartbeat_timeout_at = 0

        self._connected_at = 0
        self._closed_at = 0
        self._peer_connected_at = 0
        self._peer_closed_at = 0

        if retry_interval <= 0:
            raise ValueError("[Channel] retry_interval must be positive")
        self._retry_interval = retry_interval
        self._next_retry_at = 0

        self._ready_event = threading.Event()
        self._closed_event = threading.Event()
        self._error_event = threading.Event()

        # channel state
        self._state = Channel.State.IDLE
        self._state_thread = None
        self._error = None
        self._event_callbacks = {}

        # channel
        self._remote_address = remote_address
        options = (
            ('grpc.max_send_message_length', -1),
            ('grpc.max_receive_message_length', -1),
            ('grpc.max_reconnect_backoff_ms', 1000),
        )
        use_tls, creds = common.use_tls()
        if use_tls:
            self._channel = make_secure_channel(
                self._remote_address,
                mode=ChannelType.REMOTE,
                options=options,
                compression=compression
            )
        else:
            self._channel = make_insecure_channel(
                self._remote_address,
                mode=ChannelType.REMOTE,
                options=options,
                compression=compression
            )

        self._channel_interceptor = ClientInterceptor(
            identifier=self._identifier,
            retry_interval=self._retry_interval,
            wait_fn=self.wait_for_ready,
            check_fn=self._channel_response_check_fn,
            stats_client=stats_client)
        self._channel = grpc.intercept_channel(self._channel,
            self._channel_interceptor)

        # server
        self._listen_address = listen_address
        self._server_thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers)
        self._server_interceptor = ServerInterceptor()
        self._server = grpc.server(
            self._server_thread_pool,
            options=(
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
            ),
            interceptors=(self._server_interceptor,),
            compression=compression)

        # channel client & server
        self._channel_call = channel_pb2_grpc.ChannelStub(self._channel)
        if use_tls:
            server_credentials = grpc.ssl_server_credentials(
                ((creds[1], creds[2]), ), creds[0], True)
            self._server.add_secure_port(
                self._listen_address, server_credentials)
        else:
            self._server.add_insecure_port(self._listen_address)

        channel_pb2_grpc.add_ChannelServicer_to_server(
            Channel._Servicer(self), self._server)

        # stats
        self._stats_client = stats_client or stats.NoneClient()

    @property
    def connected_at(self):
        with self._lock:
            if self._state == Channel.State.IDLE:
                return 0
            return max(self._connected_at, self._peer_connected_at)

    @property
    def closed_at(self):
        with self._lock:
            if self._state != Channel.State.DONE:
                return 0
            return max(self._closed_at, self._peer_closed_at)

    def _channel_response_check_fn(self, response):
        self._raise_if_error()
        if response.code == channel_pb2.Code.OK:
            return
        if response.code == channel_pb2.Code.UNIDENTIFIED:
            with self._lock:
                self._emit_error(ChannelError("unidentified"))
        else:
            self._emit_error(ChannelError("unexcepted response code {} "
                "for channel resonse".format(
                    channel_pb2.Code.Name(response.code))))
        self._raise_if_error()

    def _regiser_channel_interceptor_method(self, method,
                                            request_serializer,
                                            response_deserializer):
        self._channel_interceptor.register_method(
            method, request_serializer, response_deserializer)

    # grpc channel methods
    def unary_unary(self,
                    method,
                    request_serializer=None,
                    response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.unary_unary(
            method, _request_serializer,
            _response_deserializer)

    def unary_stream(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.unary_stream(
            method, _request_serializer,
            _response_deserializer)

    def stream_unary(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.stream_unary(
            method, _request_serializer,
            _response_deserializer)

    def stream_stream(self,
                      method,
                      request_serializer=None,
                      response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.stream_stream(
            method, _request_serializer,
            _response_deserializer)

    # grpc server method
    def add_generic_rpc_handlers(self, generic_rpc_handlers):
        for handler in generic_rpc_handlers:
            self._server_interceptor.register_handler(handler.service_name())
        return self._server.add_generic_rpc_handlers(generic_rpc_handlers)

    #def _channel_callback(self, state):
    #    logging.debug("[Channel] grpc channel connectivity"
    #                  " state: %s", state.name)

    def _next_state(self, state, event):
        next_state = Channel._next_table[state].get(event)
        if next_state:
            return next_state
        return state

    def _emit_event(self, event, error=None):
        with self._lock:
            next_state = self._next_state(self._state, event)
            if self._state != next_state:
                fl_logging.info("[Channel] state changed from %s to %s, "
                                "event: %s", self._state.name,
                                next_state.name, event.name)
                self._state = next_state
                if self._state == Channel.State.ERROR:
                    assert error is not None
                    self._error_event.set()
                    fl_logging.error("[Channel] occur error: %s", str(error))
                    self._error = error
                elif self._state == Channel.State.READY:
                    self._ready_event.set()
                self._event_callback(event)
                self._condition.notify_all()

    def _emit_error(self, error):
        self._emit_event(Channel.Event.ERROR, error)

    def _event_callback(self, event):
        callbacks = self._event_callbacks.get(event, [])
        for cb in callbacks:
            cb(self, event)

    def subscribe(self, callback, event=None):
        if not event:
            for ev in Channel.Event:
                self.subscribe(callback, ev)
            return

        with self._lock:
            if not isinstance(event, Channel.Event):
                raise ValueError("[Channel] error event type")
            if event not in self._event_callbacks:
                self._event_callbacks[event] = []
            self._event_callbacks[event].append(callback)

    def error(self):
        with self._lock:
            return self._error

    def _raise_if_error(self):
        if self._error_event.is_set():
            raise self._error

    def wait_for_ready(self, timeout=None):
        succ = self._ready_event.wait(timeout)
        self._raise_if_error()
        return succ

    def wait_for_closed(self, timeout=None):
        succ = self._closed_event.wait(timeout)
        self._raise_if_error()
        return succ

    def connect(self, wait=True):
        with self._lock:
            self._raise_if_error()
            if self._state != Channel.State.IDLE:
                raise RuntimeError("[Channel] Attempting to "
                    "reconnect channel")
            self._state = Channel.State.CONNECTING_UNCONNECTED

        self._state_thread = threading.Thread(
            target=self._state_fn)
        self._state_thread.daemon = True
        self._state_thread.start()

        if wait:
            self.wait_for_ready()

    def close(self, wait=True):
        with self._lock:
            self._raise_if_error()
            if self._state == Channel.State.IDLE:
                raise RuntimeError("[Channel] Attempting to "
                    "close channel before connect")
            if self._state in (Channel.State.CONNECTING_UNCONNECTED,
                               Channel.State.CONNECTED_UNCONNECTED,
                               Channel.State.CONNECTING_CONNECTED):
                self._emit_error(ChannelError(
                    "[Channel] close unready channel"))
            else:
                self._emit_event(Channel.Event.CLOSING)
        if wait:
            self.wait_for_closed()

    def _call_locked(self, call_type):
        self._lock.release()
        try:
            req = channel_pb2.CallRequest(
                type=call_type,
                token=self._token,
                identifier=self._identifier,
                peer_identifier=self._peer_identifier)
            timer = self._stats_client.timer("channel.call_timing").start()
            res = self._channel_call.Call(req,
                                          timeout=self._heartbeat_interval,
                                          wait_for_ready=True)
            timer.stop()
        except Exception as e:
            self._stats_client.incr("channel.call_error")
            if isinstance(e, grpc.RpcError):
                fl_logging.warning("[Channel] grpc error, code: %s, "
                    "details: %s.(call type: %s)",
                    e.code(), e.details(),
                    channel_pb2.CallType.Name(call_type))
            else:
                fl_logging.error("[Channel] call error: %s.(call type: %s",
                    e, channel_pb2.CallType.Name(call_type))
            self._lock.acquire()
            return False
        self._lock.acquire()

        if res.code == channel_pb2.Code.OK:
            self._refresh_heartbeat_timeout()
            if call_type == channel_pb2.CallType.CONNECT:
                self._connected_at = res.timestamp
                self._emit_event(Channel.Event.CONNECTED)
            elif call_type == channel_pb2.CallType.CLOSE:
                self._closed_at = res.timestamp
                self._emit_event(Channel.Event.CLOSED)
            return True

        if res.code == channel_pb2.Code.UNAUTHORIZED:
            self._emit_event(Channel.Event.ERROR, ChannelError("unauthorized"))
        elif res.code == channel_pb2.Code.UNIDENTIFIED:
            if not self._peer_identifier:
                fl_logging.warning("[Channel] unidentified by peer, "
                    "but channel is clean. wait next retry")
            else:
                self._emit_error(ChannelError("unidentified"))
        else:
            msg = "unexcepted code: {} for call type: {}".format(
                channel_pb2.Code.Name(res.code),
                channel_pb2.CallType.Name(call_type))
            self._emit_error(ChannelError(msg))
        return False

    def _refresh_heartbeat_timeout(self):
        now = time.time()
        self._heartbeat_timeout_at = now + self._heartbeat_timeout
        self._next_heartbeat_at = now + self._heartbeat_interval

    def _refresh_peer_heartbeat_timeout(self):
        now = time.time()
        self._peer_heartbeat_timeout_at = now + self._heartbeat_timeout

    def _state_fn(self):
        fl_logging.debug("[Channel] thread _state_fn start")

        self._server.start()
        #self._channel.subscribe(self._channel_callback)

        self._lock.acquire()
        while True:
            now = time.time()
            saved_state = self._state
            wait_timeout = 10

            self._stats_client.gauge("channel.status", self._state.value)
            if self._state in (Channel.State.DONE, Channel.State.ERROR):
                break

            # check disconnected
            if self._state not in Channel._CONNECTING_STATES:
                if now >= self._heartbeat_timeout_at:
                    self._emit_error(ChannelError(
                        "disconnected by heartbeat timeout: {}s".format(
                            self._heartbeat_timeout)))
                    continue
                wait_timeout = min(wait_timeout,
                                   self._heartbeat_timeout_at-now)

            # check peer disconnected
            if self._state not in Channel._PEER_UNCONNECTED_STATES:
                if now >= self._peer_heartbeat_timeout_at:
                    self._emit_error(ChannelError(
                        "peer disconnected by heartbeat timeout: {}s".format(
                            self._heartbeat_timeout)))
                    continue
                wait_timeout = min(wait_timeout,
                                   self._peer_heartbeat_timeout_at-now)

            if now >= self._next_retry_at:
                self._next_retry_at = 0
                if self._state in Channel._CONNECTING_STATES:
                    if self._call_locked(channel_pb2.CallType.CONNECT):
                        self._emit_event(Channel.Event.CONNECTED)
                        self._refresh_heartbeat_timeout()
                    else:
                        self._next_retry_at = time.time() + self._retry_interval
                    continue
                if self._state in Channel._CLOSING_STATES:
                    if self._call_locked(channel_pb2.CallType.CLOSE):
                        self._emit_event(Channel.Event.CLOSED)
                        self._refresh_heartbeat_timeout()
                    else:
                        self._next_retry_at = 0 # fast retry
                    continue
                if now >= self._next_heartbeat_at:
                    if self._call_locked(channel_pb2.CallType.HEARTBEAT):
                        fl_logging.debug("[Channel] call heartbeat OK")
                        self._refresh_heartbeat_timeout()
                    else:
                        fl_logging.warning("[Channel] call heartbeat failed")
                        interval = min(self._heartbeat_interval,
                            self._retry_interval)
                        self._next_retry_at = time.time() + interval
                    continue

                wait_timeout = min(wait_timeout, self._next_heartbeat_at-now)
            else:
                wait_timeout = min(wait_timeout, self._next_retry_at-now)

            if saved_state != self._state:
                continue

            self._condition.wait(wait_timeout)

        # done
        self._lock.release()

        self._channel.close()
        time_wait = 2*self._retry_interval+self._peer_closed_at - time.time()
        if time_wait > 0:
            fl_logging.info("[Channel] wait %0.2f sec "
                         "for reducing peer close failed", time_wait)
            time.sleep(time_wait)

        self._server.stop(10)
        self._server.wait_for_termination()

        self._ready_event.set()
        self._closed_event.set()

        fl_logging.debug("[Channel] thread _state_fn stop")

    def _check_token(self, token):
        if self._token != token:
            fl_logging.debug("[Channel] peer unauthorized, got token: '%s', "
                "want: '%s'", token, self._token)
            return False
        return True

    def _check_identifier(self, identifier, peer_identifier):
        if peer_identifier and self._identifier != peer_identifier:
            return False

        if not identifier:
            return False

        if not self._peer_identifier:
            with self._lock:
                if not self._peer_identifier:
                    self._peer_identifier = identifier
                    self._server_interceptor.set_peer_identifier(
                        self._peer_identifier)

        if self._peer_identifier != identifier:
            return False

        return True

    def _call_handler(self, request, context):
        if not self._check_token(request.token):
            return channel_pb2.CallResponse(
                code=channel_pb2.Code.UNAUTHORIZED)

        if not self._check_identifier(
            request.identifier, request.peer_identifier):
            return channel_pb2.CallResponse(
                code=channel_pb2.Code.UNIDENTIFIED)

        with self._lock:
            if self._state == Channel.State.ERROR:
                return channel_pb2.CallResponse(
                    code=channel_pb2.Code.EXCEPTION)

            if request.type == channel_pb2.CallType.CONNECT:
                if self._state in Channel._PEER_CLOSED_STATES:
                    return channel_pb2.CallResponse(
                        code=channel_pb2.Code.CLOSED)
                self._emit_event(Channel.Event.PEER_CONNECTED)
                self._refresh_peer_heartbeat_timeout()
                if self._peer_connected_at == 0:
                    self._peer_connected_at = int(time.time())
                return channel_pb2.CallResponse(
                    code=channel_pb2.Code.OK,
                    timestamp=self._peer_connected_at)

            if self._state in Channel._PEER_UNCONNECTED_STATES:
                return channel_pb2.CallResponse(
                    code=channel_pb2.Code.UNCONNECTED)

            if request.type == channel_pb2.CallType.HEARTBEAT:
                self._refresh_peer_heartbeat_timeout()
                return channel_pb2.CallResponse(
                    code=channel_pb2.Code.OK,
                    timestamp=int(time.time()))

            if request.type == channel_pb2.CallType.CLOSE:
                self._emit_event(Channel.Event.PEER_CLOSED)
                self._refresh_peer_heartbeat_timeout()
                if self._peer_closed_at == 0:
                    self._peer_closed_at = int(time.time())
                return channel_pb2.CallResponse(
                    code=channel_pb2.Code.OK,
                    timestamp=self._peer_closed_at)

            return channel_pb2.CallResponse(
                code=channel_pb2.Code.UNKNOW_TYPE)

    class _Servicer(channel_pb2_grpc.ChannelServicer):
        def __init__(self, channel):
            super(Channel._Servicer, self).__init__()
            self._channel = channel

        def Call(self, request, context):
            #pylint: disable=protected-access
            return self._channel._call_handler(request, context)


def _request_serializer(request):
    return channel_pb2.SendRequest.SerializeToString(request)

def _response_deserializer(serialized_response):
    return channel_pb2.SendResponse.FromString(serialized_response)
