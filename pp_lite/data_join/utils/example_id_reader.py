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
import fsspec
import pandas as pd
from typing import List, Iterator
from pp_lite.proto.common_pb2 import FileType

CHUNK_SIZE = 16 * 1024 * 1024 * 1024


class PartitionInfo:

    def __init__(self, input_path: str):
        self._input_path = input_path
        self._num_partitions = None
        self._files = None
        self._fs = fsspec.get_mapper(input_path).fs

    @staticmethod
    def _is_valid_file(filename: str) -> bool:
        return os.path.split(filename)[1].startswith('part-')

    def _list_files(self):
        if self._files is None:
            files = [file['name'] for file in self._fs.listdir(self._input_path)]
            self._files = list(filter(self._is_valid_file, files))
        return self._files

    @property
    def num_partitions(self) -> int:
        if self._num_partitions is None:
            self._num_partitions = len(self._list_files())
        return self._num_partitions

    def get_all_files(self) -> List[str]:
        if self._fs.isfile(self._input_path):
            return [self._input_path]
        return [file['name'] for file in self._fs.listdir(self._input_path)]

    def get_files(self, partition_id: int) -> List[str]:
        """return file given partition id"""
        files = []
        try:
            for file in self._list_files():
                comp_list = os.path.split(file)[1].split('-')
                assert len(comp_list) > 1, f'split file err, file is {file}'
                comp = comp_list[1]  # as: part-04988-24de412a-0741-4157-bf0f-2e5dc4ebe2d5-c000.csv
                if comp.isdigit():
                    if int(comp) == partition_id:
                        files.append(file)
        except RuntimeError:
            logging.warning(f'[example_id_reader] get_files from {partition_id} err.')
        return files


class ExampleIdReader:

    def __init__(self, input_path: str, file_type: FileType, key_column: str):
        self._file_type = file_type
        self._input_path = input_path
        self._key_column = key_column
        self._partition_info = PartitionInfo(input_path)
        self._fs = fsspec.get_mapper(input_path).fs

    @property
    def num_partitions(self) -> int:
        return self._partition_info.num_partitions

    def _iter_data(self, filename) -> Iterator[pd.DataFrame]:
        if self._file_type == FileType.CSV:
            with self._fs.open(filename, 'r') as fin:
                df = pd.read_csv(fin, chunksize=CHUNK_SIZE)
                for chunk in df:
                    yield chunk
        else:
            raise NotImplementedError('tfrecord is not supported')

    def _data_iterator(self, partition_id: int) -> Iterator[pd.DataFrame]:
        assert partition_id < self.num_partitions
        files = self._partition_info.get_files(partition_id)
        for file in files:
            iterator = self._iter_data(filename=file)
            for data in iterator:
                yield data

    def read(self, partition_id: int) -> List:
        values = []
        for data in self._data_iterator(partition_id):
            values.extend(data[self._key_column].astype('str').to_list())
        return values

    def read_all(self) -> List[str]:
        ids = []
        for filename in self._partition_info.get_all_files():
            for part in self._iter_data(filename):
                ids.extend(part[self._key_column].astype('str').to_list())
        return ids
