# -*- coding: utf-8 -*-

import grpc
import collections
import threading
from concurrent import futures

import fedlearner.bridge.const as const
import fedlearner.bridge.util as util
from fedlearner.bridge.proto import bridge_pb2, bridge_pb2_grpc
from fedlearner.bridge.util import _method_encode, _method_decode

class _Server(grpc.Server):
    def __init__(self, bridge, listen_addr,
        compression=None,
        max_workers=None):

        self._bridge = bridge
        self._listen_addr = listen_addr

        self._thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="BridgeServerThread")
        self._server = grpc.server(
            self._thread_pool,
            compression=compression)
        self._server.add_insecure_port(self._listen_addr)
        bridge_pb2_grpc.add_BridgeServicer_to_server(
            _Server.BridgeServicer(self), self._server)

        self._lock = threading.RLock()
        self._generic_handlers = list()

    def add_generic_rpc_handlers(self, generic_handlers):
        with self._lock:
            self._generic_handlers.extend(generic_handlers)

    def add_insecure_port(self, address):
        raise NotImplementedError()

    def add_secure_port(self, address, server_credentials):
        raise NotImplementedError()

    def start(self):
        self._server.start()

    def stop(self, grace):
        self._server.stop(grace)

    def wait_for_termination(self, timeout=None):
        self._server.wait_for_termination(timeout)

    def _query_handlers(self, handler_call_details):
        for generic_handler in self._generic_handlers:
            method_handler = generic_handler.service(handler_call_details)
            if method_handler is not None:
                return method_handler
        return _not_implementd_handler

    def _abridge_metadata(self, metadata):
        identifier = None
        peer_identifier = None
        token = None
        method = None
        for pair in metadata:
            if pair[0] == const._grpc_metadata_bridge_id:
                identifier = pair[1]
            elif pair[0] == const._grpc_metadata_bridge_peer_id:
                peer_identifier = pair[1]
            elif pair[0] == const._grpc_metadata_bridge_token:
                token = pair[1]
            elif pair[0] == const._grpc_metadata_bridge_method:
                method = util._method_decode(pair[1])

        return identifier, peer_identifier, token, method

    
    def _check_or_response(self, identifier, peer_identifier, token):
        if not self._bridge._check_token(token):
            self._bridge._emit_
            return bridge_pb2.CallResponse(
                code=bridge_pb2.Code.UNAUTHROIZE)
        #if not self._bridge._check_identifier(identifier, peer_identifier):
        #    return bridge_pb2.CallResponse(
        #        code=bridge_pb2.Code.UNIDENTIFIED)

        return None

    def _call_handler(self, request, context):
        identifier, peer_identifier, token, _ =\
            self._abridge_metadata(context.invocation_metadata())
        err_res = self._check_or_response(identifier, peer_identifier, token)
        if err_res:
            return err_res
            
        return self._bridge._call_handler(request, context)

    def _send_unary_unary_handler(self, request, context):
        _, _, _, method =\
            self._abridge_metadata(context.invocation_metadata())
        handler = self._query_handlers(_HandlerCallDetails(
            _method_decode(method),
            context.invocation_metadata,
        ))

        r_req = handler.request_deserializer(request.payload)
        r_res = handler.unary_unary(r_req, context)

        return bridge_pb2.SendResponse(
            payload=handler.response_serializer(r_res)
        )
        
    def _send_unary_stream_handler(self, request, context):
        _, _, _, method =\
            self._abridge_metadata(context.invocation_metadata())
        handler = self._query_handlers(_HandlerCallDetails(
            _method_decode(method),
            context.invocation_metadata,
        ))

        r_req = handler.request_deserializer(request.payload)
        r_res_iter = handler.unary_stream(r_req, context)
        def res_iter():
            for r_res in r_res_iter:
                yield bridge_pb2.SendResponse(
                    payload=handler.response_serializer(r_res)
                )

        return res_iter()

    def _send_stream_unary_handler(self, request_iterator, context):
        _, _, _, method =\
            self._abridge_metadata(context.invocation_metadata())
        handler = self._query_handlers(_HandlerCallDetails(
            _method_decode(method),
            context.invocation_metadata,
        ))

        def r_req_iterator():
            for request in request_iterator:
                yield handler.request_deserializer(request.payload)

        r_res = handler.stream_unary(r_req_iterator(), context)

        return bridge_pb2.SendResponse(
            payload = handler.response_serializer(r_res)
        )

    def _send_stream_stream_handler(self, request_iterator, context):
        _, _, _, method =\
            self._abridge_metadata(context.invocation_metadata())
        handler = self._query_handlers(_HandlerCallDetails(
            _method_decode(method),
            context.invocation_metadata,
        ))

        ack = None

        def req_iterator():
            nonlocal ack
            for req in request_iterator:
                ack = req.seq
                yield handler.request_deserializer(req.payload)

        res_iterator = handler.stream_stream(req_iterator(), context)
        def response_iterator():
            for res in res_iterator:
                yield bridge_pb2.SendResponse(
                    ack=ack,
                    payload=handler.response_serializer(res)
                )

        return response_iterator()

    class BridgeServicer(bridge_pb2_grpc.BridgeServicer):
        def __init__(self, server):
            super(_Server.BridgeServicer, self).__init__()
            self._server = server

        def Call(self, request, context):
            return self._server._call_handler(request, context)

        def SendUnaryUnary(self, request, context):
            return self._server._send_unary_unary_handler(request, context)

        def SendUnaryStream(self, request, context):
            return self._server._send_unary_stream_handler(request, context)

        def SendStreamUnary(self, request_iterator, context):
            return self._server._send_stream_unary_handler(request_iterator, context)

        def SendStreamStream(self, request_iterator, context):
            return self._server._send_stream_stream_handler(request_iterator, context)

class _HandlerCallDetails(
        collections.namedtuple('_HandlerCallDetails', (
            'method',
            'invocation_metadata',
        )), grpc.HandlerCallDetails):
    pass

class _NotImplementedHandler(grpc.RpcMethodHandler):

    def __init__(self):
        super(_NotImplementedHandler, self).__init__()

        self.unary_unary = self._method_not_implemented
        self.unary_stream = self._method_not_implemented
        self.stream_unary = self._method_not_implemented
        self.stream_stream = self._method_not_implemented

    def request_deserializer(self, _):
        return None

    def response_serializer(self, _):
        return None

    def _method_not_implemented(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

_not_implementd_handler = _NotImplementedHandler()