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

from typing import Any, Callable, Iterator, NamedTuple, Optional, Sequence, Tuple, Union

import grpc

from fedlearner_webconsole.rpc.auth import PROJECT_NAME_HEADER, X_HOST_HEADER
from fedlearner_webconsole.rpc.v2.utils import encode_project_name


# Ref: https://github.com/d5h-foss/grpc-interceptor/blob/master/src/grpc_interceptor/client.py#L9
class _ClientCallDetailsFields(NamedTuple):
    method: str
    timeout: Optional[float]
    metadata: Optional[Sequence[Tuple[str, Union[str, bytes]]]]
    credentials: Optional[grpc.CallCredentials]
    wait_for_ready: Optional[bool]
    compression: Optional[grpc.Compression]


class ClientCallDetails(_ClientCallDetailsFields, grpc.ClientCallDetails):
    pass


RequestOrIterator = Union[Any, Iterator[Any]]


class _RpcErrorOutcome(grpc.RpcError, grpc.Future):

    def __init__(self, rpc_error: grpc.RpcError):
        super().__init__()
        self._error = rpc_error

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def running(self):
        return False

    def done(self):
        return True

    def result(self, timeout=None):
        raise self._error

    def exception(self, timeout=None):
        return self._error

    def traceback(self, timeout=None):
        return ''

    def add_done_callback(self, fn):
        fn(self)


class AuthClientInterceptor(grpc.UnaryUnaryClientInterceptor, grpc.UnaryStreamClientInterceptor,
                            grpc.StreamUnaryClientInterceptor, grpc.StreamStreamClientInterceptor):

    def __init__(self, x_host: str, project_name: Optional[str] = None):
        super().__init__()
        self.x_host = x_host
        self.project_name = project_name

    def _intercept_call(self, continuation: Callable[[ClientCallDetails, RequestOrIterator], Any],
                        client_call_details: ClientCallDetails, request_or_iterator: RequestOrIterator):
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        metadata.append((X_HOST_HEADER, self.x_host))
        if self.project_name is not None:
            metadata.append((PROJECT_NAME_HEADER, encode_project_name(self.project_name)))

        # Metadata of ClientCallDetails can not be set directly
        new_details = ClientCallDetails(client_call_details.method, client_call_details.timeout, metadata,
                                        client_call_details.credentials, client_call_details.wait_for_ready,
                                        client_call_details.compression)
        response_future = continuation(new_details, request_or_iterator)
        # This is a hack for testing only that grpc interceptor will treat testing channel's grpc error as
        # a regular response instead of an exception, whose interface is different with channel,
        # it was introduced in https://github.com/grpc/grpc/pull/17317
        if isinstance(response_future, grpc.RpcError) and not isinstance(response_future, grpc.Future):
            return _RpcErrorOutcome(response_future)
        return response_future

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        return self._intercept_call(continuation, client_call_details, request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        return self._intercept_call(continuation, client_call_details, request_iterator)
