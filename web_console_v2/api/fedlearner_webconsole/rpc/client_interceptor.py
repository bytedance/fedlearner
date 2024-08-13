# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from typing import NamedTuple, Optional, Sequence, Tuple, Union

import grpc

from fedlearner_webconsole.middleware.request_id import GrpcRequestIdMiddleware


# pylint: disable=line-too-long
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


class ClientInterceptor(grpc.UnaryUnaryClientInterceptor, grpc.UnaryStreamClientInterceptor,
                        grpc.StreamUnaryClientInterceptor, grpc.StreamStreamClientInterceptor):

    def _intercept_call(self, continuation, client_call_details, request_or_iterator):
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        # Metadata of ClientCallDetails can not be set directly
        new_details = ClientCallDetails(client_call_details.method, client_call_details.timeout,
                                        GrpcRequestIdMiddleware.add_header(metadata), client_call_details.credentials,
                                        client_call_details.wait_for_ready, client_call_details.compression)
        return continuation(new_details, request_or_iterator)

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        return self._intercept_call(continuation, client_call_details, request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        return self._intercept_call(continuation, client_call_details, request_iterator)
