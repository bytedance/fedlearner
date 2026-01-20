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
import rsa

from pp_lite.rpc.server import IServicer
from pp_lite.proto.common_pb2 import Pong, Ping
from pp_lite.proto import data_join_service_pb2, data_join_service_pb2_grpc
from pp_lite.data_join.psi_rsa.server.partition_writer import RsaServerPartitionWriter
from pp_lite.data_join.psi_rsa.server.signer import RsaDataJoinSigner
from pp_lite.data_join.psi_rsa.server.partition_reader import RsaServerPartitionReader
from pp_lite.utils.metrics import show_audit_info, emit_counter
from pp_lite.utils import metric_collector


class DataJoinServiceServicer(data_join_service_pb2_grpc.DataJoinServiceServicer, IServicer):

    def __init__(self,
                 private_key: rsa.PrivateKey,
                 input_dir: str,
                 output_dir: str,
                 signed_column: str,
                 key_column: str,
                 batch_size: int = 4096,
                 num_sign_parallel: int = 1):
        self._writer = RsaServerPartitionWriter(output_dir=output_dir, key_column=key_column)
        self._stop_hook = None
        self._signer = RsaDataJoinSigner(private_key=private_key, num_workers=num_sign_parallel)
        self._partition_reader = RsaServerPartitionReader(input_dir=input_dir,
                                                          signed_column=signed_column,
                                                          batch_size=batch_size)

    def GetPartitionNumber(self, request, context):
        emit_counter('get_partition_num', 1)
        metric_collector.emit_counter('dataset.data_join.rsa_psi.get_partition_num', 1, {'role': 'server'})
        partition_num = self._partition_reader.get_partition_num()
        logging.info(f'Receive request \'GetPartitionNum\' from client, partition num is {partition_num}')
        return data_join_service_pb2.GetPartitionNumberResponse(partition_num=partition_num)

    def GetSignedIds(self, request: data_join_service_pb2.GetSignedIdsRequest, context):
        emit_counter('get_partition', 1)
        metric_collector.emit_counter('dataset.data_join.rsa_psi.get_partition', 1, {'role': 'server'})
        partition_ids = request.partition_ids
        tip = 'without partition' if not partition_ids else f'partition {partition_ids[0]} ~ {partition_ids[-1]}'
        logging.info(f'Receive request \'GetPartition\' from client, {tip}')
        total_num = 0
        ids_generator = self._partition_reader.get_ids_generator(partition_ids)
        for ids in ids_generator:
            emit_counter('send_ids', len(ids))
            metric_collector.emit_counter('dataset.data_join.rsa_psi.send_ids', len(ids), {'role': 'server'})
            total_num = total_num + len(ids)
            logging.info(f'Sending data {tip}, sent {total_num} ids now')
            yield data_join_service_pb2.GetSignedIdsResponse(ids=ids)

    def GetPublicKey(self, request, context):
        emit_counter('get_public_key', 1)
        metric_collector.emit_counter('dataset.data_join.rsa_psi.get_public_key', 1, {'role': 'server'})
        logging.info('Receive request \'GetPublicKey\' from client')
        public_key = self._signer.public_key
        return data_join_service_pb2.PublicKeyResponse(e=str(public_key.e), n=str(public_key.n))

    def Sign(self, request: data_join_service_pb2.SignRequest, context):
        ids = [int(i) for i in request.ids]
        emit_counter('sign_time', 1)
        metric_collector.emit_counter('dataset.data_join.rsa_psi.sign_time', 1, {'role': 'server'})
        emit_counter('sign_ids', len(ids))
        metric_collector.emit_counter('dataset.data_join.rsa_psi.sign_ids', len(ids), {'role': 'server'})
        logging.info(f'Receive request \'Sign\' from client, the number of signed ids is {len(ids)}.')
        signed_ids = self._signer.sign_ids(ids)
        signed_ids = [str(i) for i in signed_ids]
        return data_join_service_pb2.SignResponse(signed_ids=signed_ids)

    def SyncDataJoinResult(self, request_iterator, context):
        emit_counter('sync_time', 1)
        metric_collector.emit_counter('dataset.data_join.rsa_psi.sync_time', 1, {'role': 'server'})
        logging.info('Receive request \'Synchronize\' from client')

        def data_generator():
            for request in request_iterator:
                yield request.partition_id, request.ids

        total_num = self._writer.write_data_join_result(data_generator())
        emit_counter('sync_ids', total_num)
        metric_collector.emit_counter('dataset.data_join.rsa_psi.sync_ids', total_num, {'role': 'server'})
        return data_join_service_pb2.SyncDataJoinResultResponse(succeeded=True)

    def Finish(self, request, context):
        self._signer.stop()
        show_audit_info()
        self._stop_hook()
        return empty_pb2.Empty()

    def HealthCheck(self, request: Ping, context):
        logging.info('Receive request \'HealthCheck\' from client')
        return Pong(message=request.message)

    def register(self, server: grpc.Server, stop_hook: Callable[[], None]):
        self._stop_hook = stop_hook
        data_join_service_pb2_grpc.add_DataJoinServiceServicer_to_server(self, server)
