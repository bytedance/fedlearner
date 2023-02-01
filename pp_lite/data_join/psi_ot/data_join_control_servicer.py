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
from typing import Callable
from google.protobuf import empty_pb2

from pp_lite.rpc.server import IServicer
from pp_lite.data_join.psi_ot.data_join_server import DataJoinServer
from pp_lite.proto.common_pb2 import Pong, Ping
from pp_lite.proto import data_join_control_service_pb2 as service_pb2
from pp_lite.proto import data_join_control_service_pb2_grpc as service_pb2_grpc
from pp_lite.proto.arguments_pb2 import ClusterSpec


class DataJoinControlServicer(service_pb2_grpc.DataJoinControlServiceServicer, IServicer):

    def __init__(self, data_join_server: DataJoinServer, cluster_spec: ClusterSpec):
        self._stop_hook = None
        self._data_join_server = data_join_server
        self._cluster_spec = cluster_spec

    def HealthCheck(self, request: Ping, context):
        logging.info('[DataJoinControlServicer] Receive HealthCheck Request')
        return Pong(message=request.message)

    def VerifyParameter(self, request: service_pb2.VerifyParameterRequest, context):
        logging.info('[DataJoinControlServicer] Receive VerifyParameter Request')
        succeeded = True
        num_partitions = self._data_join_server.num_partitions
        num_workers = len(self._cluster_spec.workers)
        if request.num_partitions != num_partitions:
            logging.warning(
                f'Server and client do not have the same partition num, {num_partitions} vs {request.num_partitions}')
            succeeded = False
        if request.num_workers != num_workers:
            logging.warning(
                f'Server and client do not have the same worker num, {num_workers} vs {request.num_workers}')
            succeeded = False
        return service_pb2.VerifyParameterResponse(succeeded=succeeded,
                                                   num_partitions=num_partitions,
                                                   num_workers=num_workers)

    def GetParameter(self, request: service_pb2.GetParameterRequest, context):
        logging.info('[DataJoinControlServicer] Receive GetParameter Request')
        num_partitions = self._data_join_server.num_partitions
        num_workers = len(self._cluster_spec.workers)
        return service_pb2.GetParameterResponse(num_partitions=num_partitions, num_workers=num_workers)

    def CreateDataJoin(self, request: service_pb2.CreateDataJoinRequest, context):
        logging.info(f'[DataJoinControlServicer] Receive CreateDataJoin Request for partition {request.partition_id}')
        assert request.type == self._data_join_server.data_join_type, 'joiner must have the same type'
        self._data_join_server.stop()
        if self._data_join_server.empty(partition_id=request.partition_id):
            logging.info(f'[DataJoinControlServicer] skip joiner for partition {request.partition_id} with input 0 ids')
            return service_pb2.CreateDataJoinResponse(succeeded=True, empty=True)
        succeeded = self._data_join_server.start(partition_id=request.partition_id)
        return service_pb2.CreateDataJoinResponse(succeeded=succeeded, empty=False)

    def GetDataJoinResult(self, request: service_pb2.GetDataJoinResultRequest, context):
        logging.info(
            f'[DataJoinControlServicer] Receive GetDataJoinResult Request for partition {request.partition_id}')
        finished = self._data_join_server.is_finished(request.partition_id)
        logging.info(f'[DataJoinControlServicer] respond result {finished} to GetDataJoinResult request')
        return service_pb2.DataJoinResult(finished=finished)

    def Finish(self, request, context):
        logging.info('[DataJoinControlServicer] Receive Finish Request')
        self._stop_hook()
        return empty_pb2.Empty()

    def register(self, server: grpc.Server, stop_hook: Callable[[], None]):
        self._stop_hook = stop_hook
        service_pb2_grpc.add_DataJoinControlServiceServicer_to_server(self, server)
