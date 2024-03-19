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
from google.protobuf import empty_pb2

from pp_lite.data_join.envs import GRPC_CLIENT_TIMEOUT

from pp_lite.proto.common_pb2 import DataJoinType, Ping, Pong
from pp_lite.proto import data_join_control_service_pb2 as service_pb2
from pp_lite.proto import data_join_control_service_pb2_grpc as service_pb2_grpc


class DataJoinControlClient:
    """Ot psi rpc client"""

    def __init__(self, server_port: int):
        logging.info(f'RpcClient started: server_port:{server_port}')
        self._host = 'localhost'
        self._server_port = server_port
        self._channel = grpc.insecure_channel(f'{self._host}:{self._server_port}')
        self._stub = service_pb2_grpc.DataJoinControlServiceStub(self._channel)

    def health_check(self, message: str = '') -> Pong:
        request = Ping(message=message)
        return self._stub.HealthCheck(request, timeout=GRPC_CLIENT_TIMEOUT)

    def verify_parameter(self, num_partitions: int, num_workers: int) -> service_pb2.VerifyParameterResponse:
        request = service_pb2.VerifyParameterRequest(num_partitions=num_partitions, num_workers=num_workers)
        return self._stub.VerifyParameter(request, timeout=GRPC_CLIENT_TIMEOUT)

    def get_parameter(self, message: str = '') -> service_pb2.GetParameterResponse:
        request = service_pb2.GetParameterRequest(message=message)
        return self._stub.GetParameter(request, timeout=GRPC_CLIENT_TIMEOUT)

    def create_data_join(self, partition_id: int, data_join_type: DataJoinType) -> service_pb2.CreateDataJoinResponse:
        request = service_pb2.CreateDataJoinRequest(partition_id=partition_id, type=data_join_type)
        # timeout is not set since server may load data from slow hdfs
        return self._stub.CreateDataJoin(request)

    def get_data_join_result(self, partition_id: int) -> service_pb2.DataJoinResult:
        request = service_pb2.GetDataJoinResultRequest(partition_id=partition_id)
        return self._stub.GetDataJoinResult(request, timeout=GRPC_CLIENT_TIMEOUT)

    def finish(self):
        logging.info('RpcClient stopped ! ! !')
        self._stub.Finish(empty_pb2.Empty())

    def close(self):
        self._channel.close()
