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
import os
from typing import Iterator, Tuple, List

import fsspec


class RsaServerPartitionWriter:

    def __init__(self, output_dir: str, key_column: str):
        self._output_dir = output_dir
        self._key_column = key_column
        self._file_system: fsspec.AbstractFileSystem = fsspec.get_mapper(self._output_dir).fs

    def _get_output_filename(self, partition_id: int = -1) -> str:
        if partition_id is None or partition_id < 0:
            return os.path.join(self._output_dir, 'joined', 'output.csv')
        return os.path.join(self._output_dir, 'joined', f'output_{partition_id}.csv')

    # TODO(zhou.yi): refactor this function by ExampleIdWriter
    def write_data_join_result(self, data_iterator: Iterator[Tuple[int, List[str]]]):
        total_num = 0

        partition_id, ids = next(data_iterator, (None, None))
        if ids is None:
            logging.warning('no joined ids received from client!')
            ids = []
        filename = self._get_output_filename(partition_id)
        if self._file_system.exists(filename):
            self._file_system.rm(filename)
        if not self._file_system.exists(os.path.dirname(filename)):
            self._file_system.makedirs(os.path.dirname(filename))
        with fsspec.open(filename, mode='w', encoding='utf-8') as f:
            f.write(self._key_column + '\n')
            f.write('\n'.join(ids) + '\n')
            tip = 'without partition' if partition_id == -1 else f'partition {partition_id}'
            total_num = total_num + len(ids)
            logging.info(f'Receive data {tip}, Synchronize {total_num} ids now')
            for partition_id, ids in data_iterator:
                f.write('\n'.join(ids) + '\n')
                total_num = total_num + len(ids)
                logging.info(f'Receive data {tip}, Synchronize {total_num} ids now')
        return total_num
