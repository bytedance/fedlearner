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
from typing import Iterator, List
from pp_lite.proto import hashed_data_join_pb2 as service_pb2
from pp_lite.proto import hashed_data_join_pb2_grpc as service_pb2_grpc
from pp_lite.data_join.utils.generators import make_ids_iterator_from_list


class HashedDataJoinClient:
    """Hashed data join for integrated test"""

    def __init__(self, server_port: int):
        self._host = 'localhost'
        self._server_port = server_port
        self._channel = grpc.insecure_channel(f'{self._host}:{self._server_port}')
        self._stub = service_pb2_grpc.HashedDataJoinServiceStub(self._channel)

    def data_join(self, ids: List[str], batch_size: int = 4096) -> Iterator[service_pb2.DataJoinResponse]:

        def request_iterator():
            for part_ids in make_ids_iterator_from_list(ids, batch_size):
                yield service_pb2.DataJoinRequest(ids=part_ids)

        response_iterator = self._stub.DataJoin(request_iterator())

        return response_iterator
