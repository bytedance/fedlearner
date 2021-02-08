# -*- coding: utf-8 -*-

import time
import uuid
import logging
import threading
import enum

import grpc

from concurrent import futures

from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc
from fedlearner.bridge.client import _Client
from fedlearner.bridge.server import _Server
from fedlearner.bridge.util import _method_encode, _method_decode, maxint

def _default_peer_stop_callback(bridge):
    logging.info("[Bridge] peer stop callback, default stop bridge")
    bridge.stop()

def _default_unauthorized_callback(bridge):
    logging.info("[Bridge] unauthorized callback, default stop bridge")
    bridge.stop()

def _default_unidentified_callback(bridge):
    logging.info("[Bridge] unidentified callback, default stop bridge")
    bridge.stop()


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

    class _Event(enum.Enum):
        CONNECTED = 0
        DISCONNECTED = 1
        CLOSING = 2
        CLOSED = 3
        PEER_CONNECTED = 4
        PEER_DISCONNECTED = 5
        PEER_CLOSED = 6

    _next_table = {
        State.IDLE: (None, None, None, None, None, None, None),
        State.CONNECTING_UNCONNECTED: (State.CONNECTED_UNCONNECTED,
            None, State.DONE, None,
            State.CONNECTING_CONNECTED, None, State.CONNECTING_CLOSED),
        State.CONNECTED_UNCONNECTED: (None,
            None, State.CLOSING_UNCONNECTED, None,
            State.READY, None, State.CONNECTED_CLOSED),
        State.CONNECTING_CONNECTED: (State.READY,
            None, State.CLOSED_CONNECTED, None,
            None, State.CONNECTING_UNCONNECTED, State.CONNECTING_CLOSED),
        State.READY: (None,
            State.CONNECTING_CONNECTED, State.CLOSING_CONNECTED, None,
            None, State.CONNECTED_UNCONNECTED, State.CONNECTED_CLOSED),
        State.CONNECTING_CLOSED: (State.CONNECTED_CLOSED,
            None, State.DONE, None,
            None, None, None),
        State.CONNECTED_CLOSED: (None,
            State.CONNECTING_CLOSED, State.CLOSING_CLOSED, State.DONE,
            None, None, None),
        State.CLOSING_UNCONNECTED: (None,
            State.DONE, None, State.DONE,
            State.CLOSING_UNCONNECTED, None, State.CLOSING_CLOSED),
        State.CLOSING_CONNECTED: (None,
            State.DONE, None, State.CLOSED_CONNECTED,
            None, State.CLOSING_UNCONNECTED, State.CLOSING_CLOSED),
        State.CLOSING_CLOSED: (None,
            State.DONE, None, State.DONE,
            None, None, None),
        State.CLOSED_CONNECTED: (None,
            None, None, None,
            None, State.DONE, State.DONE),
        State.DONE: (None, None, None, None, None, None, None),
    }
    def _next_state(state, event):
        next = Bridge._next_table[state][event.value]
        if next:
            return next
        return state



    _CALL_CONNECT_STATES = set([
        State.CONNECTING_UNCONNECTED,   
        State.CONNECTING_CONNECTED,
        State.CONNECTING_CLOSED,
    ])

    _CALL_HEARTBEAT_STATES = set([
        State.CONNECTED_UNCONNECTED,
        State.READY,
        State.CONNECTED_CLOSED, 
    ])

    _CALL_CLOSE_STATES = set([
        State.CLOSING_UNCONNECTED,
        State.CLOSING_CONNECTED,
        State.CLOSING_CLOSED,
    ])

    _PEER_CLOSED_STATUS = set([
        State.CONNECTING_CLOSED, 
        State.CONNECTED_CLOSED,
        State.CLOSING_CLOSED,
        State.DONE,
    ])

    _PEER_CONNECTED_STATES = set([
        State.CONNECTING_CONNECTED, 
        State.READY,
        State.CLOSING_CONNECTED,
        State.CLOSED_CONNECTED
    ])

    def __init__(self,
                 listen_addr,
                 remote_addr,
                 token=None,
                 peer_stop_callback=None,
                 unauthroized_callback=None,
                 unidentified_callback=None,
                 max_works=None,
                 compression=grpc.Compression.Gzip,
                 heartbeat_timeout=10,
                 retry_interval=2
                 ):

        # identifier
        self._identifier = uuid.uuid4().hex[:16]
        self._peer_identifier = None
        self._token = token

        # client
        self._client_ready = False
        self._client = _Client(self, remote_addr,
            compression)

        # server
        self._server = _Server(self, listen_addr,
            compression, max_works)

        self._peer_stop_callback = peer_stop_callback \
             if peer_stop_callback else _default_peer_stop_callback
        self._unauthroized_callback = unauthroized_callback \
             if unauthroized_callback else _default_unauthorized_callback
        self._unidentified_callback = unidentified_callback \
             if unidentified_callback else _default_unidentified_callback

        if heartbeat_timeout <= 0:
            raise ValueError("heartbeat_timeout must be positive")
        self._heartbeat_timeout = heartbeat_timeout
        self._heartbeat_interval = self._heartbeat_timeout / 5
        if self._heartbeat_interval < 1:
            self._heartbeat_interval = self._heartbeat_timeout  / 3
        self._heartbeat_timeout_at = 0
        self._peer_heartbeat_timeout_at = 0

        if retry_interval <= 0:
            raise ValueError("retry_interval must be positive")
        self._retry_interval = retry_interval
        self._next_retry_at = 0

        self._start = False
        self._stop = False

        # peer 
        self._peer_connected = False
        self._peer_closed = False

        # bridge state
        self._state_condition = threading.Condition(threading.RLock())
        self._state = Bridge.State.IDLE
        self._state_thread = None

        # notify_all if ready
        # self._ready_cv = threading.Condition(self._lock)

        # grpc channel methods
        self.unary_unary = self._client.unary_unary
        self.unary_stream = self._client.unary_stream
        self.stream_unary = self._client.stream_unary
        self.stream_stream = self._client.stream_stream

        # grpc server methods
        self.add_generic_rpc_handlers = \
            self._server.add_generic_rpc_handlers
        
    def _client_ready_callback(self, ready):
        with self._state_condition:
            if not ready:
                self._state = Bridge._next_state(self._state,
                    Bridge._Event.DISCONNECTED)
                self._state_condition.notify_all()

    def wait_for_ready(self, timeout=None):
        with self._state_condition:
            while self._state != Bridge.State.READY:
                self._state_condition.wait()

    def wait_for_stopped(self):
        with self._state_condition:
            while self._state != Bridge.State.DONE:
                self._state_condition.wait()

    def start(self, wait=False):
        with self._state_condition:
            if self._start:
                raise RuntimeError("Attempting to restart bridge")
            self._start = True
            self._state = Bridge.State.CONNECTING_UNCONNECTED

        self._state_thread = threading.Thread(
            target=self._state_fn, daemon=True)
        self._state_thread.start()

        if wait:
            self.wait_for_ready()

    def stop(self, wait=False):
        with self._state_condition:
            if not self._start:
                raise RuntimeError("Attempting to start bridge before start")
            if not self._stop: 
                self._stop = True
                self._state = Bridge._next_state(self._state,
                    Bridge._Event.CLOSING)
                self._state_condition.notify_all()

        if wait:
            self.wait_for_stopped()

    def _call(self, req):
        try:
            return self._client.call(req)
        except grpc.RpcError as e:
            logging.info("[Bridge] grpc channel return code: %s"
                ", details: %s", e.code(), e.details())
            return None
        except Exception as e:
            logging.error("[Bridge] grpc channel return error: %s", repr(e))
            return None

    def _call_connect_locked(self):
        self._state_condition.release()
        res = self._call(bridge_pb2.CallRequest(
            type=bridge_pb2.CallType.CONNECT))
        self._state_condition.acquire()
        if res == None:
            return False
        elif res.code == bridge_pb2.Code.OK:
            self._state = Bridge._next_state(self._state,
                Bridge._Event.CONNECTED)
            return True
        elif res.code == bridge_pb2.Code.CLOSED:
            logging.error("[Bridge] try to connect to a closed bridge")
        elif res.code == bridge_pb2.Code.UNAUTHORIZED:
            logging.warn("[Bridge] authentication failed")
            self._unauthroized_callback(self)
        elif res.code == bridge_pb2.Code.UNIDENTIFIED:
            logging.warn("[Bridge] unidentified bridge")
            self._unidentified_callback(self)
        else:
            logging.error("[Bridge] call connect got unexcepted code: %s",
                bridge_pb2.Code.Name(res.code))

        return False

    def _call_heartbeat_locked(self):
        self._state_condition.release()
        res = self._call(bridge_pb2.CallRequest(
            type=bridge_pb2.CallType.HEARTBEAT))
        self._state_condition.acquire()
        if res == None:
            return False
        elif res.code == bridge_pb2.Code.OK:
            return True
        elif res.code == bridge_pb2.Code.CLOSED:
            self._state = Bridge._next_state(self._state,
                Bridge._Event.DISCONNECTED)
            return True
        else:
            logging.error("[Bridge] call heartbeat got unexcepted code: %s",
                bridge_pb2.CallType.Name(res.code))

        return False

    def _call_close_locked(self):
        self._state_condition.release()
        res = self._call(bridge_pb2.CallRequest(
            type=bridge_pb2.CallType.CLOSE))
        self._state_condition.acquire()
        if res == None:
            return False
        elif res.code == bridge_pb2.Code.OK:
            self._state = Bridge._next_state(self._state,
                Bridge._Event.CLOSED)
            return True
        elif res.code == bridge_pb2.Code.CLOSED:
            self._state = Bridge._next_state(self._state,
                Bridge._Event.CLOSED)
            return True
        else:
            logging.error("[Bridge] call close got unexcepted code: %s",
                bridge_pb2.CallType.Name(res.code))
        return False

    def _state_fn(self):
        logging.debug("[Bridge] thread _state_fn start")

        self._server.start()
        self._client.subscribe(self._client_ready_callback)

        self._state_condition.acquire()
        while True:
            logging.debug("[Bridge] state: %s", self._state.name)

            now = time.time()
            wait_timeout = maxint

            if self._state == Bridge.State.DONE:
                break

            if self._state in Bridge._PEER_CONNECTED_STATES:
                if now >= self._peer_heartbeat_timeout_at:
                    logging.debug("[Bridge] peer disconnect"
                        " by heartbeat timeout")
                    self._state = Bridge._next_state(self._state,
                        Bridge._Event.PEER_DISCONNECTED)
                    continue
                wait_timeout = min(wait_timeout,
                    self._peer_heartbeat_timeout_at - now)
                
            if now >= self._next_retry_at:
                if self._state in Bridge._CALL_CONNECT_STATES:
                    if self._call_connect_locked():
                        continue
                    self._next_retry_at = time.time() + self._next_retry_at
                elif self._state in Bridge._CALL_HEARTBEAT_STATES:
                    if now >= self._heartbeat_timeout_at:
                        if self._call_heartbeat_locked():
                            self._heartbeat_timeout_at = \
                                time.time() + self._heartbeat_interval
                            continue
                        self._next_retry_at = time.time() + self._next_retry_at 
                    else:
                        wait_timeout = min(wait_timeout,
                            self._heartbeat_timeout_at - now) 
                elif self._state in Bridge._CALL_CLOSE_STATES:
                    if self._call_connect_locked():
                        continue
                    self._next_retry_at = time.time() + self._next_retry_at
            else:
               wait_timeout = min(wait_timeout,
                        self._next_retry_at - now) 


            if wait_timeout == 0:
                continue 
            elif wait_timeout == maxint:
                wait_timeout == None
            self._state_condition.notify_all()
            self._state_condition.wait(wait_timeout)

        # done
        self._state_condition.release()
        self._client.close()
        self._server.stop(None)

        logging.debug("[Bridge] thread _state_fn stop")

    def _call_handler(self, request, context):
        with self._state_condition:
            if self._state in Bridge._PEER_CLOSED_STATUS:
                return bridge_pb2.CallResponse(
                    code=bridge_pb2.Code.CLOSED)

            if request.type == bridge_pb2.CallType.CONNECT:
                self._peer_heartbeat_timeout_at = \
                    time.time() + self._heartbeat_timeout
                self._state = Bridge._next_state(self._state,
                    Bridge._Event.PEER_CONNECTED)
                self._state_condition.notify_all()
            elif request.type == bridge_pb2.CallType.HEARTBEAT:
                if not self._peer_connected:
                    return bridge_pb2.CallResponse(
                        code=bridge_pb2.Code.UNCONNECTED)
                self._peer_heartbeat_timeout_at = \
                    time.time() + self._heartbeat_timeout
            elif request.type == bridge_pb2.CallType.CLOSE:
                self._peer_connected = False
                self._peer_closed = True
                self._state_condition.notify_all()
                self._state = Bridge._next_state(self._state,
                    Bridge._Event.PEER_CLOSED)
                self._state_condition.notify_all()
            else:
                return bridge_pb2.CallResponse(code=bridge_pb2.Code.UNKNOW_TYPE)

        return bridge_pb2.CallResponse(code=bridge_pb2.Code.OK)