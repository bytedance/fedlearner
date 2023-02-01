# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import socket
from concurrent import futures
from contextlib import contextmanager
from typing import Optional, List, Callable
from unittest.mock import patch

import grpc
from grpc import ServerInterceptor
from grpc.framework.foundation import logging_pool

from testing.no_web_server_test_case import NoWebServerTestCase
from grpc_testing._channel._multi_callable import UnaryUnary


def _get_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('', 0))
        return sock.getsockname()[1]


@contextmanager
def testing_channel(register_service: Callable[[grpc.Server], None],
                    server_interceptors: Optional[List[ServerInterceptor]] = None):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1), interceptors=server_interceptors or [])
    register_service(server)
    port = _get_free_port()
    server.add_insecure_port(f'[::]:{port}')
    server.start()

    channel = grpc.insecure_channel(target=f'localhost:{port}')
    try:
        yield channel
    finally:
        server.stop(None)


class RpcClientTestCase(NoWebServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This is a bug of grpcio-testing, its interface is different with grpcio
        # TODO(linfan.fine): contribute this to grpcio-testing repo
        origin_with_call = UnaryUnary.with_call

        def new_with_call(self,
                          request,
                          timeout=None,
                          metadata=None,
                          credentials=None,
                          wait_for_ready=None,
                          compression=None):
            return origin_with_call(self=self,
                                    request=request,
                                    timeout=timeout,
                                    metadata=metadata,
                                    credentials=credentials)

        cls._with_call_patcher = patch('grpc_testing._channel._multi_callable.UnaryUnary.with_call', new=new_with_call)
        cls._with_call_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._with_call_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client_execution_pool = logging_pool.pool(1)

    def tearDown(self):
        self.client_execution_pool.shutdown(wait=False)
        super().tearDown()


class FakeRpcError(grpc.RpcError):

    def __init__(self, code, details):
        super().__init__()
        self.code = lambda: code
        self.details = lambda: details
