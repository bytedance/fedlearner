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
from typing import Iterable, List, Callable

from pp_lite.rpc.server import IServicer
from pp_lite.proto import hashed_data_join_pb2_grpc, hashed_data_join_pb2


class HashedDataJoinServicer(hashed_data_join_pb2_grpc.HashedDataJoinServiceServicer, IServicer):

    def __init__(self, ids: List[str]):
        self._ids = set(ids)
        self._inter_ids = []
        self._finished = False

    def is_finished(self):
        return self._finished

    def get_data_join_result(self) -> List[str]:
        assert self.is_finished(), 'Getting result before finished'
        return self._inter_ids

    def DataJoin(self, request_iterator: Iterable[hashed_data_join_pb2.DataJoinRequest], context):
        for part in request_iterator:
            current_inter_ids = [id for id in part.ids if id in self._ids]
            self._inter_ids.extend(current_inter_ids)
            yield hashed_data_join_pb2.DataJoinResponse(ids=current_inter_ids)
        self._finished = True

    def register(self, server: grpc.Server, stop_hook: Callable[[], None]):
        hashed_data_join_pb2_grpc.add_HashedDataJoinServiceServicer_to_server(self, server)
