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

import grpc
import logging
import threading
from typing import Callable
from concurrent import futures
from abc import ABCMeta, abstractmethod


class IServicer(metaclass=ABCMeta):

    @abstractmethod
    def register(self, server: grpc.Server, stop_hook: Callable[[], None]):
        raise NotImplementedError()


class RpcServer:

    def __init__(self, servicer: IServicer, listen_port: int):
        self._lock = threading.Lock()
        self._started = False
        self._server = None
        self._servicer = servicer
        self._listen_port = listen_port

    @property
    def server(self):
        return self._server

    def start(self):
        assert not self._started, 'already started'
        with self._lock:
            self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
            self._servicer.register(self._server, self.stop)
            self._server.add_insecure_port(f'[::]:{self._listen_port}')
            self._server.start()
            self._started = True
        logging.info(f'RpcServer started: listen_port:{self._listen_port}')

    def wait(self, timeout=None):
        self._server.wait_for_termination(timeout)

    def stop(self):
        if not self._started:
            return
        with self._lock:
            # cannot stop immediately due to Finish response will be returned
            self._server.stop(grace=5)
            del self._server
            self._started = False
        logging.info('RpcServer stopped ! ! !')

    def is_alive(self):
        with self._lock:
            return hasattr(self, '_server')
