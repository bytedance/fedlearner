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
from fedlearner_webconsole.proto.rpc.v2.system_service_pb2 import (CheckHealthRequest, CheckHealthResponse,
                                                                   ListFlagsRequest, ListFlagsResponse,
                                                                   CheckTeeEnabledRequest, CheckTeeEnabledResponse)
from fedlearner_webconsole.proto.rpc.v2.system_service_pb2_grpc import SystemServiceStub
from fedlearner_webconsole.rpc.v2.client_base import ParticipantRpcClient
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.utils.decorators.retry import retry_fn


def _default_need_retry(err: Exception) -> bool:
    return isinstance(err, grpc.RpcError)


class SystemServiceClient(ParticipantRpcClient):

    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)
        self._stub: SystemServiceStub = SystemServiceStub(channel)

    def check_health(self) -> CheckHealthResponse:
        try:
            return self._stub.CheckHealth(CheckHealthRequest())
        except grpc.RpcError as e:
            # For health check, we don't throw grpc error directly
            return CheckHealthResponse(
                healthy=False,
                message=e.details(),
            )

    def list_flags(self) -> dict:
        response: ListFlagsResponse = self._stub.ListFlags(ListFlagsRequest())
        return to_dict(response.flags)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def check_tee_enabled(self) -> CheckTeeEnabledResponse:
        return self._stub.CheckTeeEnabled(CheckTeeEnabledRequest())
