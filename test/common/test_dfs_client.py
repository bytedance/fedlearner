# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import threading
import time
import unittest

from tensorflow.compat.v1 import gfile
from fedlearner.common import dfs_client


class TestDFSClient(unittest.TestCase):
    def setUp(self):
        self.test_base_dir = "./test_dfs_base"
        if gfile.Exists(self.test_base_dir):
            gfile.DeleteRecursively(self.test_base_dir)

    def test_dfs_op(self):
        client = dfs_client.DFSClient(self.test_base_dir)
        client.delete('fl_key')
        client.set_data('fl_key', b'fl_value')
        self.assertEqual(client.get_data('fl_key'), b'fl_value')
        self.assertFalse(client.cas('fl_key', b'fl_value1', b'fl_value2'))
        self.assertTrue(client.cas('fl_key', b'fl_value', b'fl_value1'))
        self.assertEqual(client.get_data('fl_key'), b'fl_value1')

        client.delete('fl_key1')
        client.set_data('fl_key1', 'fl_value')
        self.assertEqual(client.get_data('fl_key1'), b'fl_value')
        self.assertFalse(client.cas('fl_key1', 'fl_value1', b'fl_value2'))
        self.assertTrue(client.cas('fl_key1', 'fl_value', 'fl_value1'))
        self.assertEqual(client.get_data('fl_key1'), b'fl_value1')

        self.assertTrue(client.cas('fl_key2', None, 'fl_value2'))
        self.assertEqual(client.get_data('fl_key2'), b'fl_value2')

        client.set_data('fl_key/a', '1')
        client.set_data('fl_key/b', '2')
        client.set_data('fl_key/c', '3')
        expected_kvs = [(b'fl_key', b'fl_value1'), (b'fl_key/a', b'1'),
                        (b'fl_key/b', b'2'), (b'fl_key/c', b'3')]
        for idx, kv in enumerate(client.get_prefix_kvs('fl_key')):
            self.assertEqual(kv[0], expected_kvs[idx][0])
            self.assertEqual(kv[1], expected_kvs[idx][1])
        for idx, kv in enumerate(client.get_prefix_kvs('fl_key', True)):
            print(idx, kv)
            self.assertEqual(kv[0], expected_kvs[idx+1][0])
            self.assertEqual(kv[1], expected_kvs[idx+1][1])

        self.assertTrue(client.delete_prefix('fl_key'))
        self.assertEqual(len(client.get_prefix_kvs('fl_key')), 0)
        self.assertFalse(client.delete_prefix('fl_key'))

    def test_mt_read_write(self):
        key = 'fl_key'
        value_pattern = 'value_{}'
        num_threads = 100
        values = set([value_pattern.format(i) for i in range(num_threads)])

        def read_func():
            client = dfs_client.DFSClient(self.test_base_dir)
            res = client.get_data(key)
            if res:
                res_value = res.decode()
                self.assertTrue(res_value in values)

        def write_func(idx):
            client = dfs_client.DFSClient(self.test_base_dir)
            self.assertTrue(client.set_data(key, value_pattern.format(idx)))

        reader_threads = [threading.Thread(target=read_func)
                          for _ in range(num_threads)]
        writer_threads = [threading.Thread(target=write_func, args=(idx, ))
                          for idx in range(num_threads)]
        for i in range(num_threads):
            reader_threads[i].start()
            writer_threads[i].start()
        for i in range(num_threads):
            reader_threads[i].join()
            writer_threads[i].join()

    def test_mt_cas(self):
        key = 'fl_key'
        value = 'value'
        value_pattern = 'value_{}'
        num_threads = 100
        lock = threading.Lock()
        count = []

        client = dfs_client.DFSClient(self.test_base_dir)
        client.set_data(key, value)

        def cas_func(idx):
            client = dfs_client.DFSClient(self.test_base_dir)
            time.sleep(0.01)
            succeeded = client.cas(key, value, value_pattern.format(idx))
            if succeeded:
                with lock:
                    count.append(idx)

        threads = [threading.Thread(target=cas_func, args=(i, ))
                   for i in range(num_threads)]
        for i in range(num_threads):
            threads[i].start()
        for i in range(num_threads):
            threads[i].join()
        self.assertEqual(len(count), 1)
        self.assertEqual(client.get_data(key).decode(),
                         value_pattern.format(count[0]))

    def tearDown(self) -> None:
        if gfile.Exists(self.test_base_dir):
            gfile.DeleteRecursively(self.test_base_dir)


if __name__ == '__main__':
    unittest.main()
