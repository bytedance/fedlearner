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

import grpc
import threading
from concurrent import futures
from fedlearner_webconsole.proto import (
    service_pb2, common_pb2
)


class RPCServerServicer(service_pb2.WebConsoleV2ServiceServicer):
    def __init__(self, server):
        self._server = server
    
    def CheckConnection(self, request):
        try:
            return self._server.check_connection(request)
        except Exception as e:
            return service_pb2.CheckConnectionResponse(
                status=common_pb2.STATUS_UNKNOWN_ERROR,
                msg=repr(e))

class RPCServer(object):
    def __init__(self, listen_port):
        self._listen_port = listen_port

        self._lock = threading.Lock()
        self._started = False
        self._server = None
    
    def start(self):
        assert not self._started, "Already started"

        with self._lock:
            self._server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=10))
            service_pb2.add_WebConsoleV2ServiceServicer_to_server(
                RPCServerServicer(self), self._server)
            self._server.add_insecure_port('[::]:%d' % listen_port)
            self._server.start()
            self._started = True

    def stop(self):
        if not self._started:
            return
        
        with self._lock:
            self._server.stop().wait()
            del self._server
            self._started = False

    def check_connection(self, request):
        return