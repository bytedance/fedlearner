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
from fedlearner_webconsole.proto.rpc.v2 import review_service_pb2
from fedlearner_webconsole.proto.rpc.v2.review_service_pb2_grpc import ReviewServiceStub
from fedlearner_webconsole.proto import review_pb2
from fedlearner_webconsole.rpc.v2.client_base import ParticipantRpcClient
from fedlearner_webconsole.utils.decorators.retry import retry_fn


def _default_need_retry(err: Exception) -> bool:
    return isinstance(err, grpc.RpcError)


class ReviewServiceClient(ParticipantRpcClient):

    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)
        self._stub: ReviewServiceStub = ReviewServiceStub(channel)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def create_ticket(self, ttype: review_pb2.TicketType, creator_username: str,
                      details: review_pb2.TicketDetails) -> review_pb2.Ticket:
        return self._stub.CreateTicket(
            review_service_pb2.CreateTicketRequest(
                ttype=ttype,
                creator_username=creator_username,
                details=details,
            ))

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_ticket(self, uuid: str) -> review_pb2.Ticket:
        return self._stub.GetTicket(review_service_pb2.GetTicketRequest(uuid=uuid))
