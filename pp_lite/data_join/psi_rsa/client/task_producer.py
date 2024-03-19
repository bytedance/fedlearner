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

import os
import pandas
import logging
from typing import List
from pp_lite.data_join.utils.example_id_reader import ExampleIdReader

from pp_lite.rpc.client import DataJoinClient
from pp_lite.data_join.psi_rsa.client.data_joiner import DataJoiner
from pp_lite.data_join.psi_rsa.client.signer import Signer
from pp_lite.data_join.psi_rsa.client.syncronizer import ResultSynchronizer
from pp_lite.utils.metrics import emit_counter


class TaskProducer:

    def __init__(self,
                 client: DataJoinClient,
                 reader: ExampleIdReader,
                 output_dir: str,
                 key_column: str,
                 batch_size: int,
                 num_sign_parallel: int = 5):
        self._client = client
        self._reader = reader
        self._output_dir = output_dir
        self._key_column = key_column
        self._batch_size = batch_size
        self._signer = Signer(client=self._client, num_workers=num_sign_parallel)
        self._joiner = DataJoiner(client=self._client)
        self._synchronizer = ResultSynchronizer(client=self._client)
        self._create_dirs()

    def run(self, partition_id: int):
        logging.info(f'[TaskProducer] dealing with partition{partition_id} ......')
        ids = self._read_ids(partition_id)
        if len(ids) == 0:
            logging.error('[DataReader] Input data is empty, so exit now.')
            raise ValueError('[DataReader] Input data is empty, please confirm input path')
        logging.info(f'[DataReader] the input data count is {len(ids)}')
        # sign
        signed_ids = self._signer.sign_list(ids, self._batch_size)
        signed_df = pandas.DataFrame({self._key_column: ids, 'sign': signed_ids})
        signed_df.to_csv(self._get_signed_path(partition_id), index=False)
        # join
        joined_signed_ids = self._joiner.join(signed_ids=signed_ids, partition_id=partition_id)
        singed2id = dict(zip(signed_ids, ids))
        joined_ids = [singed2id[i] for i in joined_signed_ids]
        # TODO (zhou.yi) use ExampleIdWriter to write file
        joined_df = pandas.DataFrame({self._key_column: joined_ids})
        joined_df.to_csv(self._get_joined_path(partition_id), index=False)
        # synchronize
        self._synchronizer.sync(ids=joined_ids, partition_id=partition_id)
        # update audit info
        emit_counter('Input data count', len(ids))
        emit_counter('Joined data count', len(joined_ids))

    def _read_ids(self, partition_id: int) -> List[str]:

        if partition_id < 0:
            # partition_id < 0 means the client and the server did not use the same logic to partition,
            # all client data intersect with all server data.
            return self._reader.read_all()
        return self._reader.read(partition_id)

    def _create_dirs(self):
        os.makedirs(os.path.join(self._output_dir, 'signed'), exist_ok=True)
        os.makedirs(os.path.join(self._output_dir, 'joined'), exist_ok=True)

    def _get_signed_path(self, partition_id: int) -> str:
        if partition_id < 0:
            file_path = 'signed.csv'
        else:
            file_path = f'part-{str(partition_id).zfill(5)}-signed.csv'
        return os.path.join(self._output_dir, 'signed', file_path)

    def _get_joined_path(self, partition_id: int) -> str:
        if partition_id < 0:
            file_path = 'joined.csv'
        else:
            file_path = f'part-{str(partition_id).zfill(5)}-joined.csv'
        return os.path.join(self._output_dir, 'joined', file_path)
