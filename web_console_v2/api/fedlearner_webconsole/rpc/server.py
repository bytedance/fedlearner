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

import threading
from concurrent import futures
import grpc
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)
from fedlearner_webconsole.federation.models import Federation
from fedlearner_webconsole import app


class RPCServerServicer(service_pb2_grpc.WebConsoleV2ServiceServicer):
    def __init__(self, server):
        self._server = server

    def CheckConnection(self, request, context):
        try:
            with app.app.app_context():
                return self._server.check_connection(request)
        except Exception as e:
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR,
                    msg=repr(e)))


class RPCServer(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._started = False
        self._server = None

    def start(self, listen_port):
        assert not self._started, "Already started"

        with self._lock:
            self._server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=10))
            service_pb2_grpc.add_WebConsoleV2ServiceServicer_to_server(
                RPCServerServicer(self), self._server)
            self._server.add_insecure_port('[::]:%d' % listen_port)
            self._server.start()
            self._started = True

    def stop(self):
        if not self._started:
            return

        with self._lock:
            self._server.stop(None).wait()
            del self._server
            self._started = False

    def check_auth_info(self, auth_info):
        federation = Federation.query.filter_by(
            name=auth_info.federation_name).first()
        if federation is None:
            return False
        fed_proto = federation.get_config()
        if fed_proto.self_name != auth_info.receiver_name:
            return False
        if auth_info.sender_name not in fed_proto.participants:
            return False
        party = fed_proto.participants[auth_info.sender_name]
        if party.receiver_auth_token != auth_info.auth_token:
            return False
        return True

    def check_connection(self, request):
        if self.check_auth_info(request.auth_info):
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.Status(
                    code=common_pb2.STATUS_SUCCESS))
        return service_pb2.CheckConnectionResponse(
            status=common_pb2.Status(
                code=common_pb2.STATUS_UNAUTHORIZED))
