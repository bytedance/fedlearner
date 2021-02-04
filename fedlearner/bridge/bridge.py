# -*- coding: utf-8 -*-

import os
import enum
import time
import logging
import threading
import collections

import grpc

from concurrent import futures

from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc
from fedlearner.bridge.channel import _UnaryUnaryMultiCallable, _UnaryStreamMultiCallable, \
    _StreamUnaryMultiCallable, _StreamStreamMultiCallable
from fedlearner.bridge.util import _method_encode, _method_decode

_const_grpc_metadata_method = "fl-bridge-method"
_const_grpc_metadata_auth_token = "fl-bridge-auth-token"

class _HandlerCallDetails(
        collections.namedtuple('_HandlerCallDetails', (
            'method',
            'invocation_metadata',
        )), grpc.HandlerCallDetails):
    pass

def _method_umplemented(request, context):
    """Missing associated documentation comment in .proto file."""
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

def _default_peer_stop_callback(bridge):
    logging.info("[Bridge] peer stop callback, default stop bridge")
    bridge.stop()

class Bridge():
    def __init__(self,
                 listen_addr,
                 remote_addr,
                 peer_stop_callback=None,
                 token=None,
                 max_threads=None,
                 compression=grpc.Compression.Gzip,
                 timeout=None,
                 heartbeat_timeout=30,
                 retry_interval=2
                 ):

        self._listen_addr = listen_addr
        self._remote_addr = remote_addr
        self._token = token

        self._peer_stop_callback = peer_stop_callback
        if not self._peer_stop_callback:
            self._peer_stop_callback = \
                _default_peer_stop_callback

        # lock
        self._lock = threading.RLock()

        self._timeout = None
        if timeout and timeout > 0:
            self._timeout = timeout
        self._compression = compression

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
        self._retry_interval = 1

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

        # auxiliary thread
        self._thread_control = None

        # thread pool
        if max_threads == 0:
            max_threads = os.cpu_count() * 2
        self._thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_threads,
            thread_name_prefix="BridgeThread")

        # grpc channel
        self._channel_ready = False
        self._channel = self._new_grpc_channel()

        # client
        self._client = bridge_pb2_grpc.BridgeStub(self._channel)

        # server
        self._server = grpc.server(
            self._thread_pool,
            options={
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
            },
            compression=compression)

        bridge_pb2_grpc.add_BridgeServicer_to_server(
            Bridge.BridgeServicer(self), self._server
        ) 
        self._server.add_insecure_port(listen_addr)

        # handles
        self._generic_handlers= list()
        
    def _new_grpc_channel(self):
        return grpc.insecure_channel(self._remote_addr,
            options={
                ('grpc.max_send_message_length', -1),
                ('grpc.max_receive_message_length', -1),
                ('grpc.max_reconnect_backoff_ms', 3000)
            },
            compression=self._compression
        )

    def _channel_state_fn(self, state):
        logging.debug("[Bridge] grpc channel state: %s", state.name)
        with self._control_cv:
            if state == grpc.ChannelConnectivity.IDLE \
                or state == grpc.ChannelConnectivity.CONNECTING \
                or state == grpc.ChannelConnectivity.READY:
                if not self._channel_ready:
                    logging.info("[Bridge] grpc channel ready")
                    self._channel_ready = True
                    self._ready_notify_if_need()
                    self._control_cv.notify_all()
            elif state == grpc.ChannelConnectivity.TRANSIENT_FAILURE:
                if self._channel_ready:
                    logging.info("[Bridge] grpc channel failure")
                    self._channel_ready = False
                    self._control_cv.notify_all()
            elif state == grpc.ChannelConnectivity.SHUTDOWN:
                logging.warn("[Bridge] grpc channel state: %s,"
                    " which it cannot recover."
                    " will recreate a channel", state.name)
                self._channel = self._new_grpc_channel()
                self._client = bridge_pb2_grpc.BridgeStub(self._channel)
                if self._channel_ready:
                    self._channel_ready = False
                    self._control_cv.notify_all()

    def _is_ready(self):
        return self._connected and self._peer_connected \
            and self._channel_ready and not self._closed

    def is_ready(self):
        with self._lock:
            return self._is_ready()

    def is_closed(self):
        with self._lock:
            return self._closed

    def is_stopped(self):
        with self._lock:
            return self._stopped

    def wait_for_ready(self, timeout=None):
        if self._is_ready():
            return True
        with self._ready_cv:
            if self._is_ready():
                return True
            elif self._closed:
                return False
            self._ready_cv.wait(timeout)
            return self._is_ready()

    def wait_for_stopped(self):
        with self._control_cv:
            while not self._is_stopped:
                self._control_cv.wait()

    def _ready_notify_if_need(self):
        if self._is_ready():
            self._ready_cv.notify_all()

    def start(self, wait=False):
        with self._control_cv:
            if self._start:
                raise RuntimeError("Trying repeat start bridge")
            self._start = True

        self._thread_control = threading.Thread(target=self._control_fn)
        self._thread_control.start()

        if wait:
            self.wait_for_established()

    def stop(self, wait=False):
        with self._control_cv:
            if not self._start:
                raise RuntimeError("Trying to stop a bridge before start")
            if self._stop:
                raise RuntimeError("Trying repeat stop bridge")
            self._stop = True
            self._control_cv.notify_all()

        if wait:
            self.wait_for_stopped()

    def _call(self, req):
        try:
            logging.debug("[Bridge] call request type: %s", bridge_pb2.CallType.Name(req.type))
            res = self._client.Call(req, timeout=self._timeout)
            logging.debug("[Bridge] call response code: %s", bridge_pb2.Code.Name(res.code))
        except grpc.RpcError as e:
            res = None
            logging.warn("[Bridge] call error: %s", str(e))
        except:
            raise

        return res

    def _control_fn(self):
        logging.debug("[Bridge] thread _control_fn start")

        # start bridge server
        self._server.start()

        # channel subscript and connect
        self._channel.subscribe(self._channel_state_fn,
            try_to_connect=True)

        self._lock.acquire()

        while True:
            logging.debug("[Bridge] _start: %s, _connected: %s,"
                " _peer_connected: %s, _stop: %s, _closed: %s,"
                " _peer_closed: %s, _stopped: %s",
                self._start, self._connected, self._peer_connected,
                self._stop, self._closed, self._peer_closed, self._stopped)

            type = bridge_pb2.CallType.UNSET
            now = time.time()
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
                    continue

            if self._peer_connected:
                if self._peer_heartbeat_timeout_at < now:
                    logging.debug("[Bridge] peer disconnect by heartbeat timeout")
                    self._peer_connected = False
                    continue
                wait_timeout = min(wait_timeout, self._peer_heartbeat_timeout_at - now)

            if self._connected:
                if self._heartbeat_timeout_at < now:
                    logging.debug("[Bridge] disconnect by heartbeat timeout")
                    self._connected = False
                    continue
                wait_timeout = min(wait_timeout, self._heartbeat_timeout_at - now) 
                if self._stop:
                    type = bridge_pb2.CallType.CLOSE
                else:
                    type = bridge_pb2.CallType.HEARTBEAT
            elif not self._closed:
                type = bridge_pb2.CallType.CONNECT

            elif self._peer_connected:
                logging.info("[Bridge] wait peer closed")
                self._control_cv.wait(min(wait_timeout, 3))
                continue

            res = None
            if type != bridge_pb2.CallType.UNSET:
                # wait grpc channel
                if not self._channel_ready:
                    logging.info("[Bridge] wait for grpc channel ready...")
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
                            time.time() + self._heartbeat_timeout
                        self._connected = True
                        self._ready_notify_if_need()
                        continue
                    elif type == bridge_pb2.CallType.HEARTBEAT:
                        self._heartbeat_timeout_at = \
                            time.time() + self._heartbeat_timeout
                        wait_timeout = min(wait_timeout, self._heartbeat_interval)
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
                        raise RuntimeError("unexcepted type:" \
                            " {}".format(bridge_pb2.CallType.Name(type)))
                elif res.code == bridge_pb2.Code.CLOSED:
                    if type == bridge_pb2.CallType.CONNECT:
                        logging.error("[Bridge] try to connect to a closed bridge")
                        wait_timeout = min(wait_timeout, self._retry_interval)
                    elif type == bridge_pb2.CallType.CLOSE:
                        self._connected = False
                        self._closed = True
                    elif type == bridge_pb2.CallType.HEARTBEAT:
                        self._connected = False
                    else:
                        raise RuntimeError("unexcepted type:" \
                            " {}".format(bridge_pb2.CallType.Name(type)))
                elif res.code == bridge_pb2.Code.UNAUTHORIZED:
                    logging.error("[Bridge] authentication failed")
                    wait_timeout = min(wait_timeout, self._retry_interval)
                else:
                    logging.error("[Bridge] call return unknow code: %s", res.code.name)

            if wait_timeout == 2**31:
                wait_timeout = None
            self._control_cv.notify_all()
            self._control_cv.wait(wait_timeout)

        self._lock.release()
        #done
        self._channel.close()
        self._server.stop(None)

        logging.debug("[Bridge] thread _control_fn stop")

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

    # implement grpc channel
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

    def _add_metadata(self, metadata, method):
        if not metadata:
            metadata = list()
        else:
            metadata = list(metadata)
        metadata.append(
            (_const_grpc_metadata_method, method))
        if self._token:
            metadata.append(
                (_const_grpc_metadata_auth_token, self._token))
        return metadata

    def _grpc_with_retry(self, sender, timeout=None):
        while True:
            self.wait_for_ready(timeout)
            with self._lock:
                if self._closed:
                    raise RuntimeError("Trying to send with a closed bridge")
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

        metadata = self._add_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendUnaryUnary(
                request,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                compression,
            ))

    def _send_unary_stream(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        metadata = self._add_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendUnaryStream(
                request,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                compression,
            ))

    def _send_stream_unary(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        metadata = self._add_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendStreamUnary(
                request,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                compression,
            ))

    def _send_stream_stream(self, method,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None):
        metadata = self._add_metadata(metadata, method)
        return self._grpc_with_retry(
            lambda: self._client.SendStreamStream(
                request,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                compression,
            ))

    # implement grpc server

    def add_generic_rpc_handlers(self, generic_handlers):
        self._generic_handlers.extend(generic_handlers)


    def _query_handlers(self, handler_call_details):
        for generic_handler in self._generic_handlers:
            method_handler = generic_handler.service(handler_call_details)
            if method_handler is not None:
                return method_handler
        return _method_umplemented

    def _send_unary_unary_handler(self, request, context):
        metadata = {}
        if context.invocation_metadata():
            metadata = dict(context.invocation_metadata())
        method = metadata[_const_grpc_metadata_method]
        handler_call_details = _HandlerCallDetails(
            _method_decode(method),
            None,
        )
        handler = self._query_handlers(handler_call_details)
        r_req = handler.request_deserializer(request.payload)
        r_res = handler.unary_unary(r_req, context)

        return bridge_pb2.SendResponse(
            payload=handler.response_serializer(r_res)
        )
        
    def _send_unary_stream_handler(self, request, context):
        metadata = {}
        if context.invocation_metadata():
            metadata = dict(context.invocation_metadata())
        method = metadata[_const_grpc_metadata_method]
        handler_call_details = _HandlerCallDetails(
            _method_decode(method),
            None,
        )
        handler = self._query_handlers(handler_call_details)
        r_req = handler.request_deserializer(request.payload)
        r_res_iter = handler.unary_stream(r_req, context)
        def res_iter():
            for r_res in r_res_iter:
                yield bridge_pb2.SendResponse(
                    payload=handler.response_serializer(r_res)
                )

        return res_iter()

    def _send_stream_unary_handler(self, request_iterator, context):
        metadata = {}
        if context.invocation_metadata():
            metadata = dict(context.invocation_metadata())
        method = metadata[_const_grpc_metadata_method]
        handler_call_details = _HandlerCallDetails(
            _method_decode(method),
            None,
        )
        handler = self._query_handlers(handler_call_details)
        def r_req_iterator():
            for request in request_iterator:
                yield handler.request_deserializer(request.payload)

        r_res = handler.stream_unary(r_req_iterator(), context)

        return bridge_pb2.SendResponse(
            payload = handler.response_serializer(r_res)
        )

    def _send_stream_stream_handler(self, request_iterator, context):
        metadata = {}
        if context.invocation_metadata():
            metadata = dict(context.invocation_metadata())
        method = metadata[_const_grpc_metadata_method]
        handler_call_details = _HandlerCallDetails(
            _method_decode(method),
            None,
        )
        first_request = next(request_iterator)
        handler_call_details = _HandlerCallDetails(
            _method_decode(method),
            None,
        )
        handler = self._query_handlers(handler_call_details)
        def r_req_iterator():
            yield handler.request_deserializer(first_request.payload)
            for request in request_iterator:
                yield handler.request_deserializer(request.payload)

        r_res_iter = handler.stream_stream(r_req_iterator(), context)
        def res_iter():
            for r_res in r_res_iter:
                yield bridge_pb2.SendResponse(
                    payload=handler.response_serializer(r_res)
                )

        return res_iter()

    class BridgeServicer(bridge_pb2_grpc.BridgeServicer):

        def __init__(self, bridge):
            super(Bridge.BridgeServicer, self).__init__()
            self._bridge = bridge

        def Call(self, request, context):
            return self._bridge._call_handler(request, context)

        def SendUnaryUnary(self, request, context):
            return self._bridge._send_unary_unary_handler(request, context)

        def SendUnaryStream(self, request, context):
            return self._bridge._send_unary_stream_handler(request, context)

        def SendStreamUnary(self, request_iterator, context):
            return self._bridge._send_stream_unary_handler(request_iterator, context)

        def SendStreamStream(self, request_iterator, context):
            return self._bridge._send_stream_stream_handler(request_iterator, context)