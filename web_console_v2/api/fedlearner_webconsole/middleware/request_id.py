# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import random
import threading
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Optional, List, Tuple, Union

import grpc
from flask import Flask, Response, g, request, has_request_context


class RequestIdContext(metaclass=ABCMeta):

    @abstractmethod
    def is_current_context(self) -> bool:
        pass

    @abstractmethod
    def set_request_id(self, request_id: str):
        pass

    @abstractmethod
    def get_request_id(self) -> Optional[str]:
        pass


class FlaskRequestIdContext(RequestIdContext):

    def is_current_context(self) -> bool:
        return has_request_context()

    def set_request_id(self, request_id: str):
        g.request_id = request_id

    def get_request_id(self) -> Optional[str]:
        # Defensively getting request id from flask.g
        if hasattr(g, 'request_id'):
            return g.request_id
        return None


thread_local = threading.local()


class ThreadLocalContext(RequestIdContext):

    def is_current_context(self) -> bool:
        return hasattr(thread_local, 'request_id')

    def set_request_id(self, request_id: str):
        thread_local.request_id = request_id

    def get_request_id(self) -> Optional[str]:
        # Defensively getting request id
        if hasattr(thread_local, 'request_id'):
            return thread_local.request_id
        return None


_flask_request_id_context = FlaskRequestIdContext()
_thread_local_context = ThreadLocalContext()


def _gen_request_id() -> str:
    # Random number in 4 digits
    r = f'{random.randint(0, 9999):04}'
    dt = datetime.now().strftime('%Y%m%d%H%M%S-%f')
    return f'{dt}-{r}'


class FlaskRequestId(object):

    def __init__(self, header_name='X-TT-LOGID'):
        self.header_name = header_name

    def __call__(self, app: Flask) -> Flask:
        app.before_request(self._set_request_id)
        app.after_request(self._add_header)
        return app

    def _set_request_id(self):
        # Gets existing request id or generate a new one
        request_id = request.headers.get(self.header_name) or \
                     _gen_request_id()
        _flask_request_id_context.set_request_id(request_id)

    def _add_header(self, response: Response) -> Response:
        response.headers[self.header_name] = \
            _flask_request_id_context.get_request_id()
        return response


class GrpcRequestIdMiddleware(object):
    REQUEST_HEADER_NAME = 'x-tt-logid'

    @classmethod
    def add_header(cls, metadata: List[Tuple[str, Union[str, bytes]]]):
        """Appends request id in metadata."""
        # From existing request id in context or generates a new one
        request_id = get_current_request_id() or _gen_request_id()
        metadata.append((cls.REQUEST_HEADER_NAME, request_id))

        # Sets thread local context if we get a request id
        _thread_local_context.set_request_id(request_id)
        return metadata

    @classmethod
    def set_request_id_in_context(cls, context: grpc.ServicerContext):
        """Sets request id to thread local context for gRPC service."""
        for key, value in context.invocation_metadata():
            if key == cls.REQUEST_HEADER_NAME:
                # Sets context per gRPC metadata
                _thread_local_context.set_request_id(value)
                return


def get_current_request_id() -> str:
    request_id = None
    if _flask_request_id_context.is_current_context():
        request_id = _flask_request_id_context.get_request_id()
    elif _thread_local_context.is_current_context():
        request_id = _thread_local_context.get_request_id()
    return request_id or ''
