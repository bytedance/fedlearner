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

from typing import List, Iterable

from pp_lite.rpc.client import DataJoinClient
from pp_lite.utils.decorators import retry_fn, time_log
from pp_lite.data_join.utils.generators import make_ids_iterator_from_list


class ResultSynchronizer:

    def __init__(self, client: DataJoinClient, batch_size: int = 4096):
        self._client = client
        self._batch_size = batch_size

    def sync_from_iterator(self, ids_iterator: Iterable[List[str]], partition_id: int = -1):
        self._client.sync_data_join_result(ids_iterator, partition_id)

    @time_log('Synchronizer')
    @retry_fn(retry_times=3)
    def sync(self, ids: List[str], partition_id: int = -1):
        ids_iterator = make_ids_iterator_from_list(ids, self._batch_size)
        self.sync_from_iterator(ids_iterator, partition_id)
