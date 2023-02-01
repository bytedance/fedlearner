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

import logging
from typing import List, Optional, Iterable

import grpc
from google.protobuf import empty_pb2

from pp_lite.proto.common_pb2 import Ping, Pong
from pp_lite.proto import data_join_service_pb2, data_join_service_pb2_grpc
from pp_lite.data_join.envs import GRPC_CLIENT_TIMEOUT
from pp_lite.utils.decorators import retry_fn


class DataJoinClient:
    """Rsa psi rpc client"""

    def __init__(self, server_port: int = 50052, batch_size: int = 4096):
        logging.info(f'RpcClient started: server_port:{server_port}')
        self._host = 'localhost'
        self._server_port = server_port
        self._channel = grpc.insecure_channel(f'{self._host}:{self._server_port}')
        self._stub = data_join_service_pb2_grpc.DataJoinServiceStub(self._channel)
        self._batch_size = batch_size

    @retry_fn(retry_times=30)
    def check_server_ready(self, timeout_seconds=5):
        # Check server ready via channel ready future instead of for-loop `HealthCheck` call.
        # Ref: https://grpc.github.io/grpc/python/grpc.html#grpc.channel_ready_future
        grpc.channel_ready_future(self._channel).result(timeout=timeout_seconds)

    @retry_fn(retry_times=3)
    def get_public_key(self) -> data_join_service_pb2.PublicKeyResponse:
        return self._stub.GetPublicKey(empty_pb2.Empty(), timeout=GRPC_CLIENT_TIMEOUT)

    def health_check(self) -> Pong:
        return self._stub.HealthCheck(Ping(), timeout=GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3)
    def sign(self, ids: List[str]) -> data_join_service_pb2.SignResponse:
        request = data_join_service_pb2.SignRequest(ids=ids)
        return self._stub.Sign(request, timeout=GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3)
    def get_partition_number(self) -> data_join_service_pb2.GetPartitionNumberResponse:
        return self._stub.GetPartitionNumber(empty_pb2.Empty())

    @retry_fn(retry_times=3)
    def get_signed_ids(self, partition_ids: List[int]) -> Iterable[data_join_service_pb2.GetSignedIdsResponse]:
        request = data_join_service_pb2.GetSignedIdsRequest(partition_ids=partition_ids)
        return self._stub.GetSignedIds(request)

    def sync_data_join_result(self, ids_iterator: Iterable[List[str]], partition_id: Optional[int] = None) \
            -> data_join_service_pb2.SyncDataJoinResultResponse:

        def request_iterator():
            for ids in ids_iterator:
                yield data_join_service_pb2.SyncDataJoinResultRequest(ids=ids, partition_id=partition_id)

        return self._stub.SyncDataJoinResult(request_iterator())

    def finish(self):
        logging.info('RpcClient stopped ! ! !')
        request = empty_pb2.Empty()
        self._stub.Finish(request)
