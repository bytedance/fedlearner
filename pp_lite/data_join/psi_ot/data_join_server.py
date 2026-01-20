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

from threading import Lock
import time
import logging
from typing import List
from multiprocessing import get_context

from pp_lite.proto.common_pb2 import DataJoinType
from pp_lite.data_join.psi_ot.joiner.joiner_interface import Joiner
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader
from pp_lite.data_join.utils.example_id_writer import ExampleIdWriter
from pp_lite.data_join.psi_ot.data_join_manager import MAX_NUMBER
from pp_lite.utils import metric_collector


def _run(joiner: Joiner, ids: List[str], writer: ExampleIdWriter, partition_id: int):
    # since spawn method is used, logging config is not forked from parent process,
    # so the log level should be set to INFO.
    # TODO(hangweiqiang): find a better way to initialize the process
    logging.getLogger().setLevel(logging.INFO)
    metric_collector.emit_counter('dataset.data_join.ot_or_hash_psi.partition_start_join', 1, {'role': 'server'})
    metric_collector.emit_counter('dataset.data_join.ot_or_hash_psi.row_num', len(ids), {'role': 'server'})
    inter_ids = joiner.server_run(ids)
    metric_collector.emit_counter('dataset.data_join.ot_or_hash_psi.intersection', len(inter_ids), {'role': 'server'})
    logging.info(f'[DataJoinServer] finish data join for partition {partition_id} with {len(inter_ids)} ids')
    writer.write(partition_id=partition_id, ids=inter_ids)
    writer.write_success_tag(partition_id=partition_id)
    logging.info(f'[DataJoinServer] finish write result to partition {partition_id}')


class DataJoinServer:

    def __init__(self, joiner: Joiner, reader: ExampleIdReader, writer: ExampleIdWriter):
        self._reader = reader
        self._writer = writer
        self._process = None
        self._joiner = joiner
        self._prepared_partition_id = None
        self._ids = None
        self._mutex = Lock()
        # Since DataJoinServer use multiprocessing.Process to initialize a new process to
        # run joiner, it may be blocked during fork due to https://github.com/grpc/grpc/issues/21471.
        # Setting start method to spawn will resolve this problem, the difference between fork
        # and spawn can be found in https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
        self._mp_ctx = get_context('spawn')

    @property
    def data_join_type(self) -> DataJoinType:
        return self._joiner.type

    @property
    def num_partitions(self) -> int:
        return self._reader.num_partitions

    def is_finished(self, partition_id: int) -> bool:
        return self._writer.success_tag_exists(partition_id=partition_id)

    def _get_ids(self, partition_id: int) -> List[str]:
        with self._mutex:
            if self._prepared_partition_id == partition_id:
                return self._ids
            # ensure input id is unique
            self._ids = list(set(self._reader.read(partition_id)))
            self._prepared_partition_id = partition_id
            return self._ids

    def empty(self, partition_id: int) -> bool:
        ids = self._get_ids(partition_id)
        return len(ids) == 0

    def start(self, partition_id: int) -> bool:
        """Start non-blocking joiner"""
        assert self._process is None

        with metric_collector.emit_timing('dataset.data_join.ot_or_hash_psi.read_data_timing', {'role': 'server'}):
            ids = self._get_ids(partition_id)
        logging.info(f'[DataJoinServer] read {len(ids)} ids from partition {partition_id}')

        if len(ids) < 1 or len(ids) > MAX_NUMBER:
            logging.warning(f'[DataJoinServer] len(ids) should be positive and less than {MAX_NUMBER}')
            return False

        self._process = self._mp_ctx.Process(target=_run,
                                             kwargs={
                                                 'joiner': self._joiner,
                                                 'ids': ids,
                                                 'writer': self._writer,
                                                 'partition_id': partition_id,
                                             })
        logging.info(f'[DataJoinServer] start joiner for partition {partition_id}')
        self._process.start()
        # waiting for data join server being ready
        time.sleep(10)
        return True

    def stop(self):
        """kill the joiner process and release the resources"""
        if self._process is None:
            return
        self._process.terminate()
        self._process.join()
        self._process.close()
        self._process = None
