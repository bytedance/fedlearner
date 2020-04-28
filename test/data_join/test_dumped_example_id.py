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

import unittest
import os

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import (
    example_id_dumper, example_id_visitor, common
)

class TestDumpedExampleId(unittest.TestCase):
    def setUp(self):
        self.etcd = etcd_client.EtcdClient('test_cluster', 'localhost:2379',
                                           'fedlearner', True)
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-x"
        data_source.data_source_meta.partition_num = 1
        data_source.example_dumped_dir = "./example_ids"
        self.etcd.delete_prefix(data_source.data_source_meta.name)
        self.data_source = data_source
        self.example_id_dump_options = dj_pb.ExampleIdDumpOptions(
                example_id_dump_interval=-1,
                example_id_dump_threshold=1024
            )
        if gfile.Exists(self.data_source.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source.example_dumped_dir)
        self.partition_dir = os.path.join(self.data_source.example_dumped_dir, common.partition_repr(0))
        gfile.MakeDirs(self.partition_dir)

    def _dump_example_ids(self, dumper, start_index, batch_num, batch_size):
        self.assertEqual(start_index, dumper.get_next_index())
        self.assertEqual(dumper.get_next_index(), start_index)
        index = start_index
        for i in range(batch_num):
            example_id_batch = dj_pb.LiteExampleIds(
                    partition_id=0,
                    begin_index=index
                )
            for j in range(batch_size):
                example_id_batch.example_id.append('{}'.format(index).encode())
                example_id_batch.event_time.append(150000000+index)
                self.end_index = index
                index += 1
            dumper.add_example_id_batch(example_id_batch)
            self.assertEqual(dumper.get_next_index(), index)
        dumper.finish_sync_example_id()
        self.assertTrue(dumper.need_dump())
        with dumper.make_example_id_dumper() as eid:
            eid()

    def test_example_id_dumper(self):
        example_id_dumper1 = example_id_dumper.ExampleIdDumperManager(
                self.etcd, self.data_source, 0, self.example_id_dump_options
            )
        self.assertEqual(example_id_dumper1.get_next_index(), 0)
        self._dump_example_ids(example_id_dumper1, 0, 10, 1024)
        example_id_manager = \
            example_id_visitor.ExampleIdManager(self.etcd, self.data_source, 0, True)
        last_dumped_index = example_id_manager.get_last_dumped_index()
        self.assertEqual(last_dumped_index, 10240 - 1)
        example_id_dumper2 = example_id_dumper.ExampleIdDumperManager(
                self.etcd, self.data_source, 0, self.example_id_dump_options
            )
        self.assertEqual(example_id_dumper2.get_next_index(), 10240)
        self._dump_example_ids(example_id_dumper2, 10 * 1024, 10, 1024)
        last_dumped_index = example_id_manager.get_last_dumped_index()
        self.assertEqual(last_dumped_index, 2 * 10240 - 1)

    def test_dumped_example_visitor(self):
        visitor = example_id_visitor.ExampleIdVisitor(self.etcd, self.data_source, 0)
        expected_index = 0
        for (index, example) in visitor:
            self.assertEqual(index, expected_index)
            self.assertEqual('{}'.format(index).encode(), example.example_id)
            self.assertEqual(150000000+index, example.event_time)
            self.assertEqual(index, example.index)
            expected_index += 1
        self.assertEqual(0, expected_index)
        self.assertRaises(StopIteration, visitor.seek, 200)
        self.assertTrue(visitor.finished())
        dumper = example_id_dumper.ExampleIdDumperManager(
                self.etcd, self.data_source, 0, self.example_id_dump_options
            )
        self.assertEqual(dumper.get_next_index(), 0)
        self._dump_example_ids(dumper, 0, 10, 1024)
        self.assertTrue(visitor.is_visitor_stale())
        visitor.active_visitor()
        for (index, example) in visitor:
            self.assertEqual(index, expected_index)
            self.assertEqual('{}'.format(index).encode(), example.example_id)
            self.assertEqual(150000000+index, example.event_time)
            self.assertEqual(index, example.index)
            expected_index += 1
        self.assertEqual(10240, expected_index)
        self.assertTrue(visitor.finished())
        visitor.seek(200)
        expected_index = 200
        self.assertEqual(expected_index, visitor.get_index())
        self.assertEqual(expected_index, visitor.get_item().index)
        self.assertEqual(150000000+expected_index, visitor.get_item().event_time)
        dumper2 = example_id_dumper.ExampleIdDumperManager(
                self.etcd, self.data_source, 0, self.example_id_dump_options
            )
        self._dump_example_ids(dumper2, 10240, 10, 1024)
        expected_index += 1
        self.assertTrue(visitor.is_visitor_stale())
        visitor.active_visitor()
        for (index, example) in visitor:
            self.assertEqual(index, expected_index)
            self.assertEqual('{}'.format(index).encode(), example.example_id)
            self.assertEqual(150000000+index, example.event_time)
            self.assertEqual(index, example.index)
            expected_index += 1
        self.assertEqual(10240 * 2, expected_index)
        visitor2 = example_id_visitor.ExampleIdVisitor(self.etcd, self.data_source, 0)
        visitor2.seek(886)
        expected_index = 886
        self.assertEqual(expected_index, visitor2.get_index())
        self.assertEqual(expected_index, visitor2.get_item().index)
        self.assertEqual(150000000+expected_index, visitor2.get_item().event_time)
        expected_index += 1
        for (index, example) in visitor2:
            self.assertEqual(index, expected_index)
            self.assertEqual('{}'.format(index).encode(), example.example_id)
            self.assertEqual(150000000+index, example.event_time)
            self.assertEqual(index, example.index)
            expected_index += 1
        self.assertEqual(10240 * 2, expected_index)

    def tearDown(self):
        if gfile.Exists(self.data_source.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source.example_dumped_dir)

if __name__ == '__main__':
    unittest.main()
