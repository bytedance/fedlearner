# -*- coding: utf-8 -*-

import time
import uuid
import logging
import threading
import enum
import grpc
from concurrent import futures


from fedlearner.bridge import bridge_pb2, bridge_pb2_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType
from fedlearner.bridge.client_interceptor import RetryInterceptor, \
    WaitInterceptor
from fedlearner.bridge.server_interceptor import AckInterceptor

maxint = 2**32-1

class Bridge():
    class State(enum.Enum):
        IDLE                   = 0
        CONNECTING_UNCONNECTED = 1
        CONNECTED_UNCONNECTED  = 2
        CONNECTING_CONNECTED   = 3
        READY                  = 4
        CONNECTING_CLOSED      = 5
        CONNECTED_CLOSED       = 7
        CLOSING_UNCONNECTED    = 8
        CLOSING_CONNECTED      = 9
        CLOSING_CLOSED         = 10
        CLOSED_CONNECTED       = 11
        DONE                   = 12

    class Event(enum.Enum):
        CONNECTED = 0
        DISCONNECTED = 1
        CLOSING = 2
        CLOSED = 3
        PEER_CONNECTED = 4
        PEER_DISCONNECTED = 5
        PEER_CLOSED = 6
        UNAUTHORIZED = 7
        UNIDENTIFIED = 8
        PEER_UNAUTHORIZED = 9
        PEER_UNIDENTIFIED = 10

    _next_table = {
        State.IDLE: {},
        State.CONNECTING_UNCONNECTED: {
            Event.CONNECTED: State.CONNECTED_UNCONNECTED,
            Event.CLOSING: State.DONE,
            Event.PEER_CONNECTED: State.CONNECTING_CONNECTED,
        },
        State.CONNECTED_UNCONNECTED: {
            Event.CLOSING: State.CLOSING_UNCONNECTED,
            Event.PEER_CONNECTED: State.READY,
        },
        State.CONNECTING_CONNECTED: {
            Event.CONNECTED: State.READY,
            Event.CLOSING: State.DONE,
            Event.PEER_DISCONNECTED: State.CONNECTING_UNCONNECTED,
            Event.PEER_CLOSED: State.CONNECTING_CLOSED,
        },
        State.READY: {
            Event.DISCONNECTED: State.CONNECTING_CONNECTED,
            Event.CLOSING: State.CLOSING_CONNECTED,
            Event.PEER_DISCONNECTED: State.CONNECTED_UNCONNECTED,
            Event.PEER_CLOSED: State.CONNECTED_CLOSED,
        },
        State.CONNECTING_CLOSED: {
            Event.CONNECTED: State.CONNECTED_CLOSED,
            Event.CLOSING: State.DONE,
        },
        State.CONNECTED_CLOSED: {
            Event.DISCONNECTED: State.CONNECTING_CLOSED,
            Event.CLOSING: State.CLOSING_CLOSED,
            Event.CLOSED: State.DONE,
        },
        State.CLOSING_UNCONNECTED: {
            Event.CLOSED: State.DONE,
            Event.PEER_CONNECTED: State.CLOSING_CONNECTED
        },
        State.CLOSING_CONNECTED: {
            Event.CLOSED: State.CLOSED_CONNECTED,
            Event.PEER_DISCONNECTED: State.DONE,
            Event.PEER_CLOSED: State.CLOSING_CLOSED,
        },
        State.CLOSING_CLOSED: {
            Event.DISCONNECTED: State.DONE,
            Event.CLOSED: State.DONE,
        },
        State.CLOSED_CONNECTED: {
            Event.PEER_DISCONNECTED :State.DONE,
            Event.PEER_CLOSED :State.DONE,
        },
        State.DONE: {},
    }

    _UNCONNECTED_STATES = set([
        State.CONNECTING_UNCONNECTED,   
        State.CONNECTING_CONNECTED,
        State.CONNECTING_CLOSED,
    ])

    _CONNECTED_STATES = set([
        State.CONNECTED_UNCONNECTED,
        State.READY,
        State.CONNECTED_CLOSED, 
    ])

    _CLOSING_STATES = set([
        State.CLOSING_UNCONNECTED,
        State.CLOSING_CONNECTED,
        State.CLOSING_CLOSED,
    ])

    _READY_STATUS = set([
        State.READY,
        State.CONNECTED_CLOSED,
    ])

    _PEER_CONNECTED_STATES = set([
        State.CONNECTING_CONNECTED, 
        State.READY,
        State.CLOSING_CONNECTED,
        State.CLOSED_CONNECTED
    ])

    _PEER_CLOSED_STATUS = set([
        State.CONNECTING_CLOSED,
        State.CONNECTED_CLOSED, 
        State.CLOSING_CLOSED,
        State.DONE,
    ])

    def __init__(self,
                 listen_address,
                 remote_address,
                 token=None,
                 max_workers=None,
                 compression=grpc.Compression.Gzip,
                 heartbeat_timeout=60,
                 retry_interval=2):
        # identifier
        self._identifier = uuid.uuid4().hex[:16]
        self._peer_identifier = ""
        self._token = token if token else ""

        # lock & condition
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        if heartbeat_timeout <= 0:
            raise ValueError("heartbeat_timeout must be positive")
        self._heartbeat_timeout = heartbeat_timeout
        self._heartbeat_interval = self._heartbeat_timeout / 4
        self._heartbeat_timeout_at = 0
        self._peer_heartbeat_timeout_at = 0

        self._connected_at = 0
        self._peer_connected_at = 0

        if retry_interval <= 0:
            raise ValueError("retry_interval must be positive")
        self._retry_interval = retry_interval
        self._next_retry_at = 0

        self._ready_event = threading.Event()
        self._termination_event = threading.Event()

        # bridge state
        self._state = Bridge.State.IDLE
        self._state_thread = None
        self._event_condition = threading.Condition(self._lock)
        self._event_set = set()
        self._event_callbacks = {}

        # channel
        self._remote_address = remote_address
        self._channel = make_insecure_channel(
            self._remote_address,
            mode=ChannelType.REMOTE,
            options={
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
                ('grpc.max_reconnect_backoff_ms', 2000)
            },
            compression=compression
        )
        self._channel_retry_interceptor = RetryInterceptor(self._retry_interval)
        self._channel_wait_interceptor = WaitInterceptor(self.wait_for_ready)
        self._channel = grpc.intercept_channel(self._channel, 
            self._channel_retry_interceptor,
            self._channel_wait_interceptor)

        # server
        self._listen_address = listen_address
        self._server_thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="BridgeServerThread")
        self._server = grpc.server(
            self._server_thread_pool,
            interceptors=(AckInterceptor(),),
            compression=compression)
        self._server.add_insecure_port(self._listen_address)

        # bridge client & server
        self._bridge_call = bridge_pb2_grpc.BridgeStub(self._channel)
        bridge_pb2_grpc.add_BridgeServicer_to_server(
            Bridge._Servicer(self), self._server)

        # grpc server methods
        self.add_generic_rpc_handlers = \
            self._server.add_generic_rpc_handlers

    def _regiser_channel_interceptor_method(self, method,
                                            request_serializer,
                                            response_deserializer):
        self._channel_wait_interceptor.register_method(method)
        self._channel_retry_interceptor.register_method(
            method, request_serializer, response_deserializer)


    # grpc channel methods
    def unary_unary(self,
                    method,
                    request_serializer=None,
                    response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.unary_unary(
            method, request_serializer, response_deserializer)

    def unary_stream(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.unary_stream(
            method, request_serializer, response_deserializer)

    def stream_unary(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.stream_unary(
            method, request_serializer, response_deserializer)

    def stream_stream(self,
                      method,
                      request_serializer=None,
                      response_deserializer=None):
        self._regiser_channel_interceptor_method(method,
            request_serializer, response_deserializer)
        return self._channel.stream_stream(
            method, RetryInterceptor.stream_stream_request_serializer,
            RetryInterceptor.stream_stream_response_deserializer)

    # grpc server method
    def add_generic_rpc_handlers(self, generic_rpc_handlers):
        return self._server.add_generic_rpc_handlers(generic_rpc_handlers)

    def _channel_callback(self, state):
        #logging.debug("[Bridge] grpc channel callback state: %s", state.name)
        if state == grpc.ChannelConnectivity.IDLE \
            or state == grpc.ChannelConnectivity.CONNECTING \
            or state == grpc.ChannelConnectivity.READY:
            ready = True
        elif state == grpc.ChannelConnectivity.TRANSIENT_FAILURE \
            or state == grpc.ChannelConnectivity.SHUTDOWN:
            ready = False

        if ready:
            # nothing to do
            return

        with self._lock:
            if self._state in Bridge._CONNECTED_STATES:
                self._emit_event(Bridge.Event.DISCONNECTED)

    def _next_state(state, event):
        next = Bridge._next_table[state].get(event)
        if next:
            return next
        return state

    def _emit_event(self, event):
        with self._lock:
            next_state = Bridge._next_state(self._state, event)
            if self._state != next_state:
                logging.info("[Bridge] receive effective event: %s,"
                    " current state: %s, next state: %s",
                    event.name, self._state.name, next_state.name)
                self._state = next_state
                self._condition.notify_all()
            self._event_set.add(event)
            self._event_condition.notify_all()

    def _event_callback_fn(self):
        while True:
            with self._lock:
                while len(self._event_set) == 0:
                    if self._state == Bridge.State.DONE:
                        return
                    self._event_condition.wait()
                event = self._event_set.pop()
                callbacks = self._event_callbacks.get(event, [])
            # run callback unlock
            for callback in callbacks:
                callback(self, event)

    def subscribe(self, callback):
        for event in Bridge.Event:
            self.subscribe_event(event, callback)

    def subscribe_event(self, event, callback):
        with self._lock:
            if self._state != Bridge.State.IDLE:
                raise RuntimeError("Attempting to subscribe"
                    " a started bridge event")
            if type(event) != Bridge.Event:
                raise ValueError("error event type")
            if event not in self._event_callbacks:
                self._event_callbacks[event] = []
            self._event_callbacks[event].append(callback)

    def wait_for_ready(self, timeout=None):
        return self._ready_event.wait(timeout)

    def wait_for_termination(self, timeout=None):
        return self._termination_event.wait(timeout)

    def start(self, wait=False):
        with self._lock:
            if self._state != Bridge.State.IDLE:
                raise RuntimeError("Attempting to restart bridge")
            self._state = Bridge.State.CONNECTING_UNCONNECTED

        self._state_thread = threading.Thread(
            target=self._state_fn, daemon=True)
        self._state_thread.start()

        if wait:
            self.wait_for_ready()

    def stop(self, wait=False):
        with self._lock:
            if self._state == Bridge.State.IDLE:
                raise RuntimeError("Attempting to stop bridge before start")
            self._emit_event(Bridge.Event.CLOSING)

        if wait:
            self.wait_for_termination()

    def _call_locked(self, req):
        self._lock.release()
        try:
            res = self._bridge_call.Call(req)
        except grpc.RpcError as e:
            logging.info("[Bridge] grpc channel return code: %s"
                ", details: %s", e.code(), e.details())
            res = None
        except Exception as e:
            logging.error("[Bridge] grpc channel return error: %s", repr(e))
            res = None
        self._lock.acquire()
        return res

    def _call_connect_locked(self):
        res = self._call_locked(bridge_pb2.CallRequest(
            type=bridge_pb2.CallType.CONNECT,
            token=self._token,
            identifier=self._identifier,
            peer_identifier=self._peer_identifier))
        if res == None:
            return False

        if res.code == bridge_pb2.Code.OK:
            self._emit_event(Bridge.Event.CONNECTED)
        elif res.code == bridge_pb2.Code.UNAUTHORIZED:
            logging.warn("[Bridge] authentication failed")
            self._emit_event(Bridge.Event.UNAUTHORIZED)
            return False
        elif res.code == bridge_pb2.Code.UNIDENTIFIED:
            logging.warn("[Bridge] unidentified bridge")
            self._emit_event(Bridge.Event.UNIDENTIFIED)
            return False
        else:
            logging.error("[Bridge] call connect got unexcepted code: %s",
                bridge_pb2.Code.Name(res.code))
            return False
        return True

    def _call_heartbeat_locked(self):
        res = self._call_locked(bridge_pb2.CallRequest(
            type=bridge_pb2.CallType.HEARTBEAT,
            token=self._token,
            identifier=self._identifier,
            peer_identifier=self._peer_identifier))
        if res == None:
            return False

        if res.code == bridge_pb2.Code.OK:
            pass
        elif res.code == bridge_pb2.Code.UNCONNECTED:
            logging.warn("[Bridge] disconnected by peer response")
            self._emit_event(Bridge.Event.DISCONNECTED)
            return False
        elif res.code == bridge_pb2.Code.UNAUTHORIZED:
            logging.warn("[Bridge] authentication failed")
            self._emit_event(Bridge.Event.UNAUTHORIZED)
            return False
        elif res.code == bridge_pb2.Code.UNIDENTIFIED:
            logging.warn("[Bridge] unidentified bridge")
            self._emit_event(Bridge.Event.UNIDENTIFIED)
            return False
        else:
            logging.error("[Bridge] call heartbeat got unexcepted code: %s",
                bridge_pb2.Code.Name(res.code))
            return False
        return True

    def _call_close_locked(self):
        res = self._call_locked(bridge_pb2.CallRequest(
            type=bridge_pb2.CallType.CLOSE,
            token=self._token,
            identifier=self._identifier,
            peer_identifier=self._peer_identifier))
        if res == None:
            return False

        if res.code == bridge_pb2.Code.OK:
            self._emit_event(Bridge.Event.CLOSED)
        elif res.code == bridge_pb2.Code.UNAUTHORIZED:
            logging.warn("[Bridge] authentication failed")
            self._emit_event(Bridge.Event.UNAUTHORIZED)
            return False
        elif res.code == bridge_pb2.Code.UNIDENTIFIED:
            logging.warn("[Bridge] unidentified bridge")
            self._emit_event(Bridge.Event.UNIDENTIFIED)
            return False
        elif res.code == bridge_pb2.Code.CLOSED:
            self._emit_event(Bridge.Event.CLOSED)
        else:
            logging.error("[Bridge] call close got unexcepted code: %s",
                bridge_pb2.Code.Name(res.code))
            return False
        return True

    def _state_fn(self):
        logging.debug("[Bridge] thread _state_fn start")

        logging.info("[Bridge] remote_address: %s, listen_address: %s",
            self._remote_address, self._listen_address)
        self._server.start()
        self._channel.subscribe(self._channel_callback)
        event_thread = threading.Thread(
            target=self._event_callback_fn, daemon=True)
        event_thread.start()

        self._lock.acquire()
        while True:
            now = time.time()
            saved_state = self._state
            wait_timeout = maxint

            if self._state == Bridge.State.DONE:
                self._event_condition.notify_all()
                break

            if self._state in Bridge._READY_STATUS:
                if not self._ready_event.is_set():
                    logging.info("[Bridge] bridge is ready")
                    self._ready_event.set()
            else:
                self._ready_event.clear()

            if self._state in Bridge._PEER_CONNECTED_STATES:
                if now >= self._peer_heartbeat_timeout_at:
                    logging.debug("[Bridge] peer disconnect"
                        " by heartbeat timeout")
                    self._emit_event(Bridge.Event.PEER_DISCONNECTED)
                    continue

            if now >= self._next_retry_at:
                self._next_retry_at = 0
                if self._state in Bridge._UNCONNECTED_STATES:
                    if not self._call_connect_locked():
                        self._next_retry_at = \
                            time.time() + self._retry_interval
                        wait_timeout = min(wait_timeout,
                            self._retry_interval)
                elif self._state in Bridge._CONNECTED_STATES:
                    if now >= self._heartbeat_timeout_at:
                        self._call_heartbeat_locked()
                        self._heartbeat_timeout_at = \
                            time.time() + self._heartbeat_interval
                        wait_timeout = min(wait_timeout,
                            self._heartbeat_interval)
                    else:
                        wait_timeout = min(wait_timeout,
                            self._heartbeat_timeout_at - now)
                elif self._state in Bridge._CLOSING_STATES:
                    if not self._call_close_locked():
                        self._next_retry_at = \
                            time.time() + self._retry_interval
                        wait_timeout = min(wait_timeout,
                            self._retry_interval)
            else:
                wait_timeout = min(wait_timeout, self._next_retry_at - now)

            if saved_state != self._state:
                continue

            if wait_timeout != maxint:
                self._condition.wait(wait_timeout)
            else:
                self._condition.wait()

        # done
        self._lock.release()
        self._channel.close()
        self._server.stop(None)
        self._server.wait_for_termination()

        self._ready_event.set()
        self._termination_event.set()

        logging.debug("[Bridge] thread _state_fn stop")

    def _check_token(self, token):
        if self._token != token:
            logging.debug("[Bridge] peer unauthorized, got token: '%s'"
                ", want: '%s'", token, self._token)
            self._emit_event(Bridge.Event.PEER_UNAUTHORIZED)
            return False
        return True

    def _check_identifier(self, identifier, peer_identifier):
        if peer_identifier and self._identifier != peer_identifier:
            self._emit_event(Bridge.Event.PEER_UNIDENTIFIED)
            return False

        if not identifier:
            self._emit_event(Bridge.Event.PEER_UNIDENTIFIED)
            return False

        if not self._peer_identifier:
            with self._lock:
                if not self._peer_identifier:
                    self._peer_identifier = identifier

        if self._peer_identifier != identifier:
            self._emit_event(Bridge.Event.PEER_UNIDENTIFIED)
            return False

        return True

    def _call_handler(self, request, context):
        if not self._check_token(request.token):
            return bridge_pb2.CallResponse(
                code=bridge_pb2.Code.UNAUTHORIZED)
        
        if not self._check_identifier(
            request.identifier, request.peer_identifier):
            return bridge_pb2.CallResponse(
                code=bridge_pb2.Code.UNIDENTIFIED)

        with self._lock:
            if self._state in Bridge._PEER_CLOSED_STATUS:
                return bridge_pb2.CallResponse(
                    code=bridge_pb2.Code.CLOSED)

            if request.type == bridge_pb2.CallType.CONNECT:
                self._peer_heartbeat_timeout_at = \
                    time.time() + self._heartbeat_timeout
                self._emit_event(Bridge.Event.PEER_CONNECTED)
            elif request.type == bridge_pb2.CallType.HEARTBEAT:
                if self._state not in Bridge._PEER_CONNECTED_STATES:
                    return bridge_pb2.CallResponse(
                        code=bridge_pb2.Code.UNCONNECTED)
                self._peer_heartbeat_timeout_at = \
                    time.time() + self._heartbeat_timeout
            elif request.type == bridge_pb2.CallType.CLOSE:
                self._emit_event(Bridge.Event.PEER_CLOSED)
            else:
                return bridge_pb2.CallResponse(
                        code=bridge_pb2.Code.UNKNOW_TYPE)
            return bridge_pb2.CallResponse(
                code=bridge_pb2.Code.OK)



    class _Servicer(bridge_pb2_grpc.BridgeServicer):
        def __init__(self, bridge):
            super(Bridge._Servicer, self).__init__()
            self._bridge = bridge

        def Call(self, request, context):
            return self._bridge._call_handler(request, context)