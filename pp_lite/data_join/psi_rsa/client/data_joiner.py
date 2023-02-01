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

from pp_lite.rpc.client import DataJoinClient
from pp_lite.utils.decorators import time_log


class DataJoiner:

    def __init__(self, client: DataJoinClient, partition_batch_size: int = 10):
        self._client = client
        self._partition_batch_size = partition_batch_size

    def _get_partition(self, partition_id: int) -> Iterable[Optional[List[str]]]:
        partition_list = [partition_id]
        if partition_id == -1:
            part_num = self._client.get_partition_number().partition_num
            partition_list = list(range(part_num))

        for i in range(0, len(partition_list), self._partition_batch_size):
            batch = partition_list[i:i + self._partition_batch_size]
            for resp in self._client.get_signed_ids(partition_ids=batch):
                yield resp.ids

    @time_log('Joiner')
    def join(self, signed_ids: List[str], partition_id: int = -1):
        hash_table = set(signed_ids)
        intersection_ids = []
        # TODO: implement multiprocess consumer
        for ids in self._get_partition(partition_id):
            if ids is None:
                continue
            logging.info(f'[Joiner] {len(ids)} ids received from server')
            inter = [i for i in ids if i in hash_table]
            intersection_ids.extend(inter)
            logging.info(f'[Joiner] {len(intersection_ids)} ids joined')
        # remove duplicate elements
        return list(set(intersection_ids))
