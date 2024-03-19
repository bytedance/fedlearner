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
import logging
from typing import List

from pp_lite.data_join.psi_ot.joiner.joiner_interface import Joiner
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader
from pp_lite.data_join.utils.example_id_writer import ExampleIdWriter
from pp_lite.rpc.data_join_control_client import DataJoinControlClient
from pp_lite.utils.decorators import retry_fn, timeout_fn
from pp_lite.utils import metric_collector

MAX_NUMBER = 16000000


class DataJoinManager:

    def __init__(self, joiner: Joiner, client: DataJoinControlClient, reader: ExampleIdReader, writer: ExampleIdWriter):
        self._reader = reader
        self._writer = writer
        self._client = client
        self._joiner = joiner

    def _wait_for_server_finished(self, partition_id: int):
        for i in range(10):
            resp = self._client.get_data_join_result(partition_id=partition_id)
            if resp.finished:
                logging.info(f'[DataJoinManager] server is finished for partition {partition_id}')
                return
            logging.warning(f'[DataJoinManager] server is still not finished for partition {partition_id}')
            time.sleep(10)
        raise Exception('server is still not finished!')

    @retry_fn(3)
    @timeout_fn(1200)
    def _run_task(self, joiner: Joiner, partition_id: int):
        logging.info(f'[DataJoinManager] start partition {partition_id}')
        # ensure input id is unique
        with metric_collector.emit_timing('dataset.data_join.ot_or_hash_psi.read_data_timing', {'role': 'client'}):
            ids = list(set(self._reader.read(partition_id)))
        if len(ids) == 0:
            logging.info(f'[DataJoinManager] skip join for partition {partition_id} with client input 0 ids')
            return
        response = self._client.create_data_join(partition_id=partition_id, data_join_type=joiner.type)
        if response.empty:
            logging.info(f'[DataJoinManager] skip join for partition {partition_id} with server input 0 ids')
            return
        logging.info(f'[DataJoinManager] start join for partition {partition_id} with input {len(ids)} ids')
        assert len(ids) < MAX_NUMBER, f'the number of id should be less than {MAX_NUMBER}'
        metric_collector.emit_counter('dataset.data_join.ot_or_hash_psi.partition_start_join', 1, {'role': 'client'})
        metric_collector.emit_counter('dataset.data_join.ot_or_hash_psi.row_num', len(ids), {'role': 'client'})
        inter_ids = joiner.client_run(ids=ids)
        metric_collector.emit_counter('dataset.data_join.ot_or_hash_psi.intersection', len(inter_ids),
                                      {'role': 'client'})
        logging.info(f'[DataJoinManager] finish join for partition {partition_id} with output {len(inter_ids)} ids')
        self._writer.write(partition_id=partition_id, ids=inter_ids)
        self._wait_for_server_finished(partition_id=partition_id)
        self._writer.write_success_tag(partition_id=partition_id)
        logging.info(f'[DataJoinManager] finish writing result for partition {partition_id}')

    def run(self, partition_ids: List[int]):
        logging.info('[DataJoinManager] data join start!')
        for partition_id in partition_ids:
            if self._writer.success_tag_exists(partition_id=partition_id):
                logging.warning(f'[DataJoinManager] skip partition {partition_id} since success tag exists')
                continue
            self._run_task(joiner=self._joiner, partition_id=partition_id)
        self._client.finish()
        logging.info('[DataJoinManager] data join is finished!')
