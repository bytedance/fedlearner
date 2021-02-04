# -*- coding: utf-8 -*-

import time
import uuid
import logging
import threading

import grpc

from concurrent import futures

from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc
from fedlearner.bridge.client import _Client
from fedlearner.bridge.server import _Server
from fedlearner.bridge.util import _method_encode, _method_decode

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

        # lock
        self._lock = threading.RLock()

        self._control_cv = threading.Condition(self._lock)
        self._start = False
        self._stop = False
        self._connected = False
        self._peer_connected = False
        self._closed = False
        self._peer_closed = False
        self._stopped = False

        # notify_all if _connected and _peer_connected
        self._ready_cv = threading.Condition(self._lock)

        # grpc channel methods
        self.unary_unary = self._client.unary_unary
        self.unary_stream = self._client.unary_stream
        self.stream_unary = self._client.stream_unary
        self.stream_stream = self._client.stream_stream

        # grpc server methods
        self.add_generic_rpc_handlers = \
            self._server.add_generic_rpc_handlers
        
    def _client_ready_callback(self, ready):
        with self._control_cv:
            if self._client_ready == ready:
                return
            self._client_ready = ready
            if not self._client_ready \
                and self._connected:
                self._connected = False
            self._control_cv.notify_all()

    @property
    def is_ready(self):
        with self._lock:
            return self._ready

    @property
    def is_closed(self):
        with self._lock:
            return self._closed

    @property
    def is_stopped(self):
        with self._lock:
            return self._stopped

    @property
    def _ready(self):
        return self._connected and self._peer_connected

    def _ready_notify_if_need(self):
        if self._ready:
            self._ready_cv.notify_all()

    def wait_for_ready(self, timeout=None):
        if self._ready: # lock free
            return True
        with self._ready_cv:
            if self._ready:
                return True
            elif self._closed:
                return False
            self._ready_cv.wait(timeout)
            return self._ready

    def wait_for_stopped(self):
        with self._control_cv:
            while not self._stopped:
                self._control_cv.wait()

    def start(self, wait=False):
        with self._control_cv:
            if self._start:
                raise RuntimeError(
                    "Attempting to start bridge repeatedly")
            self._start = True

        control_thread = threading.Thread(target=self._control_fn, daemon=True)
        control_thread.start()

        if wait:
            self.wait_for_ready()

    def stop(self, wait=False):
        with self._control_cv:
            if not self._start:
                raise RuntimeError("Attempting to start bridge before start")
            if self._stop: 
                raise RuntimeError("Attempting to stop bridge repeatedly")
            self._stop = True
            self._control_cv.notify_all()

        if wait:
            self.wait_for_stopped()

    def _control_fn(self):
        logging.debug("[Bridge] thread _control_fn start")

        self._server.start()
        self._client.subscribe(self._client_ready_callback)

        self._lock.acquire()
        while True:
            logging.debug("[Bridge] _start: %s, _connected: %s,"
                " _peer_connected: %s, _stop: %s, _closed: %s,"
                " _peer_closed: %s, _stopped: %s",
                self._start, self._connected,
                self._peer_connected, self._stop, self._closed,
                self._peer_closed, self._stopped)

            now = time.time()
            type = bridge_pb2.CallType.UNSET
            wait_timeout = 2**32-1

            if self._closed and self._peer_closed:
                self._stopped = True
                self._ready_cv.notify_all()
                self._control_cv.notify_all()
                break
                
            if self._stop \
                and not self._closed and not self._connected:
                self._closed = True
                continue

            if self._stop \
                and not self._peer_closed and not self._peer_connected:
                self._peer_closed = True
                continue

            if not self._stop and self._peer_closed:
                if self._peer_stop_callback:
                    self._peer_stop_callback(self)
                    self._peer_stop_callback = None

            if self._peer_connected:
                if self._peer_heartbeat_timeout_at < now:
                    logging.debug("[Bridge] peer disconnect"
                        " by heartbeat timeout")
                    self._peer_connected = False
                    continue
                else:
                    wait_timeout = min(wait_timeout,
                        self._peer_heartbeat_timeout_at - now)

            if self._connected:
                if self._stop:
                    type = bridge_pb2.CallType.CLOSE
                elif self._heartbeat_timeout_at < now:
                    type = bridge_pb2.CallType.HEARTBEAT
                else:
                    wait_timeout = min(wait_timeout,
                        self._heartbeat_timeout_at - now)
            elif not self._closed:
                type = bridge_pb2.CallType.CONNECT

            elif self._peer_connected:
                logging.info("[Bridge] wait peer closed")
                self._control_cv.wait(min(wait_timeout, 3))
                continue

            res = None
            if type != bridge_pb2.CallType.UNSET:
                # wait client ready
                if not self._client_ready:
                    logging.info("[Bridge] wait for client ready...")
                    self._control_cv.wait(min(wait_timeout, 3))
                    continue
                self._lock.release()
                # unlock
                res = self._call(bridge_pb2.CallRequest(type=type))
                # lock again
                self._lock.acquire()
                if res == None:
                    wait_timeout = min(wait_timeout, self._retry_interval)

            if res != None:
                if res.code == bridge_pb2.Code.OK:
                    if type == bridge_pb2.CallType.CONNECT:
                        self._heartbeat_timeout_at = \
                            time.time() + self._heartbeat_interval
                        self._connected = True
                        self._ready_notify_if_need()
                        continue
                    elif type == bridge_pb2.CallType.HEARTBEAT:
                        self._heartbeat_timeout_at = \
                            time.time() + self._heartbeat_interval
                        wait_timeout = min(wait_timeout, \
                            self._heartbeat_interval)
                    elif type == bridge_pb2.CallType.CLOSE:
                        self._connected = False
                        self._closed = True
                        continue
                    else:
                        raise RuntimeError("unexcepted type:" \
                            " {}".format(bridge_pb2.CallType.Name(type)))
                elif res.code == bridge_pb2.Code.UNCONNECTED:
                    if type == bridge_pb2.CallType.HEARTBEAT:
                        self._connected = False
                        continue
                    elif type == bridge_pb2.CallType.CLOSE:
                        self._connected = False
                        self._closed = True
                        continue
                    else:
                        raise RuntimeError("unexcepted response code:" \
                            " {}, for calltype: {}".format( \
                                bridge_pb2.Code.Name(res.code),
                                bridge_pb2.CallType.Name(type)
                            ))
                elif res.code == bridge_pb2.Code.CLOSED:
                    if type == bridge_pb2.CallType.CONNECT:
                        logging.error("[Bridge] try to connect to"
                            " a closed bridge")
                        wait_timeout = min(wait_timeout, self._retry_interval)
                    elif type == bridge_pb2.CallType.CLOSE:
                        self._connected = False
                        self._closed = True
                    elif type == bridge_pb2.CallType.HEARTBEAT:
                        self._connected = False
                    else:
                        raise RuntimeError("unexcepted response code:" \
                            " {}, for calltype: {}".format( \
                                bridge_pb2.Code.Name(res.code),
                                bridge_pb2.CallType.Name(type)
                            ))
                elif res.code == bridge_pb2.Code.UNAUTHORIZED:
                    if type == bridge_pb2.CallType.CONNECT \
                        or type == bridge_pb2.CallType.HEARTBEAT:
                        logging.warn("[Bridge] authentication failed")
                        wait_timeout = min(wait_timeout, self._retry_interval)
                        self._unauthroized_callback(self)
                    else:
                        raise RuntimeError("unexcepted response code:" \
                            " {}, for calltype: {}".format( \
                                bridge_pb2.Code.Name(res.code),
                                bridge_pb2.CallType.Name(type)
                            ))
                elif res.code == bridge_pb2.Code.UNIDENTIFIED:
                    if type == bridge_pb2.CallType.CONNECT \
                        or type == bridge_pb2.CallType.HEARTBEAT:
                        logging.warn("[Bridge] unidentified bridge")
                        wait_timeout = min(wait_timeout, self._retry_interval)
                        self._unidentified_callback(self)
                    else:
                        raise RuntimeError("unexcepted response code:" \
                            " {}, for calltype: {}".format( \
                                bridge_pb2.Code.Name(res.code),
                                bridge_pb2.CallType.Name(type)
                            ))
                else:
                    logging.error("[Bridge] call return unknow code: %s", res.code.name)

            if wait_timeout == 2**31:
                wait_timeout = None
            self._control_cv.notify_all()
            self._control_cv.wait(wait_timeout)

        # done
        self._lock.release()
        self._client.close()
        self._server.stop(None)

        logging.debug("[Bridge] thread _control_fn stop")

    def _call(self, req):
        try:
            logging.debug("[Bridge] call request type: %s", bridge_pb2.CallType.Name(req.type))
            res = self._client.call(req)
            logging.debug("[Bridge] call response code: %s", bridge_pb2.Code.Name(res.code))
        except grpc.RpcError as e:
            res = None
            logging.warn("[Bridge] call error: %s", str(e))
        except:
            raise

        return res

    def _call_handler(self, request, context):
        with self._control_cv:
            if request.type == bridge_pb2.CallType.CONNECT:
                if self._peer_closed:
                    return bridge_pb2.CallResponse(
                        code=bridge_pb2.Code.CLOSED)

                self._peer_heartbeat_timeout_at = \
                    time.time() + self._heartbeat_timeout
                if not self._peer_connected:
                    self._peer_connected = True
                    self._ready_notify_if_need()
                    self._control_cv.notify_all()
            elif request.type == bridge_pb2.CallType.HEARTBEAT:
                if self._peer_closed:
                    return bridge_pb2.CallResponse(
                        code=bridge_pb2.Code.CLOSED)
                if not self._peer_connected:
                    return bridge_pb2.CallResponse(
                        code=bridge_pb2.Code.UNCONNECTED)

                self._peer_heartbeat_timeout_at = \
                    time.time() + self._heartbeat_timeout
                # no notify
            elif request.type == bridge_pb2.CallType.CLOSE:
                self._peer_connected = False
                self._peer_closed = True
                self._control_cv.notify_all()
            else:
                return bridge_pb2.CallResponse(code=bridge_pb2.Code.UNKNOW_TYPE)

        return bridge_pb2.CallResponse(code=bridge_pb2.Code.OK)