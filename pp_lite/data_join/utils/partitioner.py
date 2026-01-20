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
import csv
import fcntl
import shutil
import threading
import logging
import pyarrow as pa
import pyarrow.csv as _csv
from cityhash import CityHash64  # pylint: disable=no-name-in-module
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor


def get_partition_path(output_path: str, partition_id: int):
    return os.path.join(output_path, f'part-{partition_id}')


def read_ids(input_path: str, key_column: str, block_size: int, num_partitions: int, queue: Queue):
    t = threading.current_thread()
    read_options = _csv.ReadOptions(block_size=block_size)
    with _csv.open_csv(input_path, read_options=read_options) as reader:
        for chunk in reader:
            if chunk is None:
                break
            raw_df = chunk.to_pandas()
            raw_df[key_column] = raw_df[key_column].astype('str')
            raw_df['partition_id'] = [CityHash64(i) % num_partitions for i in raw_df[key_column]]
            groups = raw_df.groupby('partition_id')
            for group in groups:
                partition_id, data = group
                data.drop(columns=['partition_id'], inplace=True)
                table = pa.Table.from_pandas(data, preserve_index=False)
                group = (partition_id, table)
                queue.put(group)
                logging.info(f'[Reader]: Put {table.num_rows} ids with partition id {partition_id} into queue of size '
                             f'{queue.qsize()} ------ Thread_id: {t.ident}')


def write_partitioned_ids(output_path: str, queue: Queue):
    try:
        while True:
            t = threading.current_thread()
            partition_id, table = queue.get(timeout=30)
            logging.info(f'[Writer]: Get {table.num_rows} ids with partition id {partition_id} from queue of size '
                         f'{queue.qsize()} ------ Thread_id: {t.ident}')
            path = get_partition_path(output_path, partition_id)
            with open(path, 'ab') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                option = _csv.WriteOptions(include_header=False)
                _csv.write_csv(table, f, option)
    except Empty as e:
        logging.info('writer exits due to getting no data from queue')


class PartReader:

    def __init__(self, input_path: str, num_partitions: int, block_size: int, key_column: str, reader_thread_num: int):
        self._input_path = input_path
        self._num_partitions = num_partitions
        self._block_size = block_size
        self._key_column = key_column
        self._pool = ThreadPoolExecutor(max_workers=reader_thread_num)

    def __del__(self):
        self._pool.shutdown(wait=True)
        logging.info('[Reader] ThreadPoolExecutor has shutdown.')

    def read(self, queue: Queue):
        for filename in os.listdir(self._input_path):
            self._pool.submit(read_ids, os.path.join(self._input_path, filename), self._key_column, self._block_size,
                              self._num_partitions, queue)


class PartWriter:

    def __init__(self, output_path: str, num_partitions: int, writer_thread_num: int):
        self._output_path = output_path
        self._num_partitions = num_partitions
        self._pool = ThreadPoolExecutor(max_workers=writer_thread_num)

    def __del__(self):
        self._pool.shutdown(wait=True)
        logging.info('[Writer] ThreadPoolExecutor has shutdown.')

    def write(self, queue: Queue):
        for _ in range(20):
            self._pool.submit(write_partitioned_ids, self._output_path, queue)


class Partitioner:

    def __init__(self, input_path: str, output_path: str, num_partitions: int, block_size: int, key_column: str,
                 queue_size: int, reader_thread_num: int, writer_thread_num: int):
        self._input_path = input_path
        self._output_path = output_path
        self._num_partitions = num_partitions
        self._block_size = block_size
        self._key_column = key_column
        self._queue = Queue(queue_size)
        self._reader_thread_num = reader_thread_num
        self._writer_thread_num = writer_thread_num
        shutil.rmtree(self._output_path, ignore_errors=True)
        os.makedirs(self._output_path, exist_ok=True)

    def partition_data(self) -> None:
        header = [self._key_column]
        for filename in os.listdir(self._input_path):
            input_path = os.path.join(self._input_path, filename)
            with open(input_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames
            break

        for i in range(self._num_partitions):
            with open(get_partition_path(self._output_path, i), 'w', encoding='utf-8') as f:
                writer = csv.DictWriter(f, header)
                writer.writeheader()
        reader = PartReader(self._input_path, self._num_partitions, self._block_size, self._key_column,
                            self._reader_thread_num)
        writer = PartWriter(self._output_path, self._num_partitions, self._writer_thread_num)
        reader.read(self._queue)
        writer.write(self._queue)
