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

import time
from typing import List
from pp_lite.data_join.psi_ot.joiner.joiner_interface import Joiner
from pp_lite.data_join.psi_ot.joiner.utils import HashValueSet
from pp_lite.proto.common_pb2 import DataJoinType
from pp_lite.rpc.server import RpcServer
from pp_lite.rpc.hashed_data_join_client import HashedDataJoinClient
from pp_lite.data_join.psi_ot.joiner.hashed_data_join_servicer import HashedDataJoinServicer


class HashedDataJoiner(Joiner):

    @property
    def type(self) -> DataJoinType:
        return DataJoinType.HASHED_DATA_JOIN

    def client_run(self, ids: List[str]) -> List[str]:
        client = HashedDataJoinClient(server_port=self.joiner_port)
        hash_value_set = HashValueSet()
        hash_value_set.add_raw_values(ids)
        response_iterator = client.data_join(hash_value_set.get_hash_value_list())
        resp_ids = []
        for part in response_iterator:
            for response_hashed_id in part.ids:
                resp_ids.append(hash_value_set.get_raw_value(response_hashed_id))
        return resp_ids

    def server_run(self, ids: List[str]) -> List[str]:
        hash_value_set = HashValueSet()
        hash_value_set.add_raw_values(ids)
        servicer = HashedDataJoinServicer(ids=hash_value_set.get_hash_value_list())
        server = RpcServer(servicer=servicer, listen_port=self.joiner_port)
        server.start()
        for _ in range(1000):
            if servicer.is_finished():
                raw_ids = [hash_value_set.get_raw_value(hash_id) for hash_id in servicer.get_data_join_result()]
                return raw_ids
            time.sleep(1)
        raise Exception('data join is not finished')
