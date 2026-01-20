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
import threading
import queue
from time import sleep
from typing import Iterator, Optional, Generator, List
from pathlib import Path

import pandas
import fsspec

from pp_lite.utils.decorators import retry_fn
from pp_lite.data_join.utils.generators import make_ids_iterator_from_list


def _get_part_id(filename: str) -> Optional[int]:
    """extract partition id from filename"""
    comp = filename.split('-')
    for c in comp:
        if c.isdecimal():
            return int(c)
    return None


def _filter_files(files: Iterator[str], partition_ids: List[int]) -> Iterator:
    """
    Args:
        files(Iterator): files iterator under input dir
        partition_ids(List[int]): target file number
    Returns:
        the files have the same number with partition_ids
    """
    file_list = []
    for file in files:
        if file.startswith('part-'):
            if _get_part_id(file) in partition_ids:
                file_list.append(file)
    return file_list


# TODO (zhou.yi): use ExampleIdReader to read
class RsaServerPartitionReader():

    def __init__(self, input_dir: str, signed_column: str, batch_size: int):
        self._input_dir = input_dir
        self._signed_column = signed_column
        self._batch_size = batch_size
        self._file_system: fsspec.AbstractFileSystem = fsspec.get_mapper(self._input_dir).fs
        self._partition_num = self._set_partition_num()

    def _get_files_under(self, path: str) -> List[str]:
        return [
            Path(file.get('name')).name
            for file in self._file_system.ls(path, detail=True)
            if file.get('type') == 'file'
        ]

    @staticmethod
    def _is_valid_file(filename: str) -> bool:
        return filename.startswith('part-')

    def _set_partition_num(self) -> int:
        files = self._get_files_under(self._input_dir)
        return len(list(filter(self._is_valid_file, files)))

    def get_partition_num(self) -> int:
        return self._partition_num

    def _get_files_by_partition_id(self, partition_ids: List[int]) -> List[str]:
        files = self._get_files_under(self._input_dir)
        if not partition_ids:
            files = filter(self._is_valid_file, files)
        else:
            files = _filter_files(files=files, partition_ids=partition_ids)
        files = [os.path.join(self._input_dir, file) for file in files]
        return files

    def get_ids_generator(self, partition_ids: List[int]) -> Generator:

        files = self._get_files_by_partition_id(partition_ids)
        with _BufferedReader(files, self._signed_column) as reader:
            for keys in reader.read_keys():
                for ids in make_ids_iterator_from_list(keys, self._batch_size):
                    yield ids


class _BufferedReader(object):
    """A reader to get keys from files.

    It uses producer-consumer pattern to speed up.
    """
    _FILE_CAPACITY = 5
    _WAIT_TIME_SECONDS = 1

    def __init__(self, file_list: List[str], key_column: str):
        self._read_thread = threading.Thread(target=self._get_keys_from_files, name='Buffered Reader', daemon=True)
        self._data_queue = queue.Queue(maxsize=self._FILE_CAPACITY)
        self._file_list = file_list
        self._key_column = key_column
        self._exception = None
        self._finish = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            self._read_thread.join()

    def read_keys(self):
        self._read_thread.start()
        while True:
            if self._exception:
                logging.exception(f'read keys with exception: {str(self._exception)}')
                raise self._exception
            # NOTE: this is not thread-safe
            if self._data_queue.empty():
                if self._finish:
                    break
                sleep(self._WAIT_TIME_SECONDS)
            else:
                yield self._data_queue.get()

    def _get_keys_from_files(self):
        try:
            # Reads keys per file
            for file in self._file_list:
                df = read_csv(file)
                keys = df[self._key_column].astype('str')
                self._data_queue.put(keys)
            self._finish = True
        # pylint: disable=broad-except
        except Exception as e:
            self._exception = e


# reading from hdfs may fail and exit, so add retry
@retry_fn(retry_times=3)
def read_csv(file_path: str) -> pandas.DataFrame:
    with fsspec.open(file_path, mode='r') as f:
        logging.debug(f'Read file {file_path}...')
        return pandas.read_csv(f)
