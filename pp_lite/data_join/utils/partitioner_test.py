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

import csv
import os
import logging
import pandas
import shutil
import tempfile
import time
import unittest
from queue import Queue
from pp_lite.data_join.utils.partitioner import read_ids, write_partitioned_ids, Partitioner


def make_data(num: int, path: str, num_line: int) -> None:
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)

    for i in range(num):
        data = range(i * num_line, (i + 1) * num_line)
        ids = [{'oaid': oaid, 'x1': oaid} for oaid in data]
        with open(os.path.join(path, f'part-{i}'), 'wt', encoding='utf-8') as f:
            writer = csv.DictWriter(f, ['oaid', 'x1'])
            writer.writeheader()
            writer.writerows(ids)


class PartitionTest(unittest.TestCase):

    def test_read_ids(self):
        with tempfile.TemporaryDirectory() as input_path:
            make_data(1, input_path, 10)
            filename = f'{input_path}/part-0'
            queue = Queue(20)
            read_ids(filename, 'oaid', 1000, 2, queue)
            id1, table1 = queue.get()
            self.assertEqual(id1, 0)
            self.assertEqual(table1.to_pandas().values.tolist(), [['7', 7]])
            id2, table2 = queue.get()
            self.assertEqual(id2, 1)
            self.assertEqual(table2.to_pandas().values.tolist(),
                             [['0', 0], ['1', 1], ['2', 2], ['3', 3], ['4', 4], ['5', 5], ['6', 6], ['8', 8], ['9', 9]])

            # 1 partition
            filename = f'{input_path}/part-0'
            queue = Queue(20)
            read_ids(filename, 'oaid', 1000, 1, queue)
            id1, table1 = queue.get()
            self.assertEqual(id1, 0)
            self.assertEqual(
                table1.to_pandas().values.tolist(),
                [['0', 0], ['1', 1], ['2', 2], ['3', 3], ['4', 4], ['5', 5], ['6', 6], ['7', 7], ['8', 8], ['9', 9]])

    def test_write_ids(self):
        with tempfile.TemporaryDirectory() as input_path:
            make_data(1, input_path, 10)
            filename = f'{input_path}/part-0'
            queue = Queue(20)
            num_partitions = 2
            block_size = 1000
            read_ids(filename, 'oaid', block_size, num_partitions, queue)
            with tempfile.TemporaryDirectory() as output_path:
                write_partitioned_ids(output_path, queue)
                self.assertEqual(len(os.listdir(output_path)), 2)
                self.assertTrue(os.path.exists(os.path.join(output_path, 'part-0')))
                self.assertTrue(os.path.exists(os.path.join(output_path, 'part-1')))
                with open(os.path.join(output_path, 'part-0'), encoding='utf-8') as fin:
                    self.assertEqual(fin.read(), '"7",7\n')
                with open(os.path.join(output_path, 'part-1'), encoding='utf-8') as fin:
                    self.assertEqual(fin.read(), '"0",0\n"1",1\n"2",2\n"3",3\n"4",4\n"5",5\n"6",6\n"8",8\n"9",9\n')

            # 1 partition
            read_ids(filename, 'oaid', block_size, 1, queue)
            with tempfile.TemporaryDirectory() as output_path:
                write_partitioned_ids(output_path, queue)
                self.assertEqual(len(os.listdir(output_path)), 1)
                self.assertTrue(os.path.exists(os.path.join(output_path, 'part-0')))
                with open(os.path.join(output_path, 'part-0'), encoding='utf-8') as fin:
                    self.assertEqual(fin.read(),
                                     '"0",0\n"1",1\n"2",2\n"3",3\n"4",4\n"5",5\n"6",6\n"7",7\n"8",8\n"9",9\n')

    def test_partitioner(self):
        with tempfile.TemporaryDirectory() as input_path:
            make_data(20, input_path, 10)
            with tempfile.TemporaryDirectory() as output_path:
                timeout = 30
                partitioner = Partitioner(input_path=input_path,
                                          output_path=output_path,
                                          num_partitions=20,
                                          block_size=10000000,
                                          key_column='oaid',
                                          queue_size=40,
                                          reader_thread_num=20,
                                          writer_thread_num=20)
                start = time.time()
                partitioner.partition_data()
                logging.info(f'Partitioner use time {time.time() - start - timeout}s')
                self.assertEqual(len(os.listdir(output_path)), 20)
                df = pandas.read_csv(os.path.join(output_path, 'part-0'))
                self.assertEqual(sorted(df.values.tolist()),
                                 [[22, 22], [71, 71], [94, 94], [120, 120], [127, 127], [136, 136], [173, 173]])

            # 1 partition
            with tempfile.TemporaryDirectory() as output_path:
                timeout = 30
                partitioner = Partitioner(input_path=input_path,
                                          output_path=output_path,
                                          num_partitions=1,
                                          block_size=10000000,
                                          key_column='oaid',
                                          queue_size=40,
                                          reader_thread_num=20,
                                          writer_thread_num=20)
                start = time.time()
                partitioner.partition_data()
                logging.info(f'Partitioner use time {time.time() - start - timeout}s')
                self.assertEqual(len(os.listdir(output_path)), 1)
                df = pandas.read_csv(os.path.join(output_path, 'part-0'))
                self.assertEqual(len(df.values.tolist()), 200)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    unittest.main()
