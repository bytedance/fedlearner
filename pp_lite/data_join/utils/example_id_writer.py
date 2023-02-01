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
import fsspec
import logging
import pandas as pd
from typing import List


class ExampleIdWriter:

    def __init__(self, output_path: str, key_column: str):
        self._output_path = output_path
        self._key_column = key_column
        self._fs = fsspec.get_mapper(output_path).fs

    def write(self, partition_id: int, ids: List[str]):
        if not self._fs.exists(self._output_path):
            self._fs.makedirs(self._output_path, exist_ok=True)
        filename = os.path.join(self._output_path, f'partition_{partition_id}')
        logging.debug(f'[ExampleIdWriter] start writing {len(ids)} ids for partition {partition_id} to {filename}')
        with self._fs.open(filename, 'w') as f:
            df = pd.DataFrame(data={self._key_column: ids})
            df.to_csv(f, index=False)
        logging.debug(f'[ExampleIdWriter] finish writing for partition {partition_id}')

    def combine(self, num_partitions: int):
        if not os.path.isfile(os.path.join(self._output_path, 'partition_0')):
            logging.warning('[ExampleIdWriter] combine fail, as no partition file')
            return
        self._fs.copy(os.path.join(self._output_path, 'partition_0'), os.path.join(self._output_path, 'output.csv'))
        for partition in range(1, num_partitions):
            with self._fs.open(os.path.join(self._output_path, 'output.csv'), 'ab') as o:
                with self._fs.open(os.path.join(self._output_path, f'partition_{partition}')) as partition:
                    partition.readline()
                    o.write(partition.read())

    def _success_tag(self, partition_id: int) -> str:
        return os.path.join(self._output_path, f'{partition_id:04}._SUCCESS')

    def write_success_tag(self, partition_id: int):
        self._fs.touch(self._success_tag(partition_id))
        logging.debug(f'[ExampleIdWriter] write success tag for partition {partition_id}')

    def success_tag_exists(self, partition_id: int) -> bool:
        return self._fs.exists(self._success_tag(partition_id))
