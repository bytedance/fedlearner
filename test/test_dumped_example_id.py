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

import tensorflow as tf
from tensorflow.python.platform import gfile

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import (
    example_id_dumper, example_id_visitor
)

class TestDumpedExampleId(unittest.TestCase):
    def setUp(self):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-x"
        data_source.data_source_meta.partition_num = 1
        data_source.example_dumped_dir = "./example_ids"
        self.data_source = data_source
        if gfile.Exists(self.data_source.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source.example_dumped_dir)
        self.partition_dir = os.path.join(self.data_source.example_dumped_dir, 'partition_0')
        gfile.MakeDirs(self.partition_dir)
        self._example_id_dumper = example_id_dumper.ExampleIdDumperManager(
                self.data_source, 0)
        self.assertEqual(self._example_id_dumper.get_next_index(), 0)
        index = 0
        for i in range(5):
            req = dj_pb.SyncExamplesRequest(
                    data_source_meta=data_source.data_source_meta,
                    partition_id=0,
                    begin_index=index
                )
            for j in range(1 << 15):
                req.example_id.append('{}'.format(index).encode())
                req.event_time.append(150000000+index)
                self.end_index = index
                index += 1
            self._example_id_dumper.append_synced_example_req(req)
            self.assertEqual(self._example_id_dumper.get_next_index(), index)
        self._example_id_dumper.finish_sync_example()
        self.assertTrue(self._example_id_dumper.need_dump())
        self._example_id_dumper.dump_example_ids()

    def test_dumped_example_visitor(self):
        example_id_manager = example_id_visitor.ExampleIdManager(self.data_source, 0)
        visitor = example_id_visitor.ExampleIdVisitor(example_id_manager)
        expected_index = 0
        for (index, example) in visitor:
            self.assertEqual(index, expected_index)
            self.assertEqual('{}'.format(index).encode(), example.example_id)
            self.assertEqual(150000000+index, example.event_time)
            self.assertEqual(index, example.index)
            expected_index += 1
        self.assertEqual(self.end_index, index)
        try:
            visitor.seek(1 << 30)
        except StopIteration:
            self.assertTrue(True)
            self.assertTrue(visitor.finished())
        else:
            self.assertTrue(False)
        index, example = visitor.seek(500)
        self.assertFalse(visitor.finished())
        expected_index = 500
        self.assertEqual(index, expected_index)
        self.assertEqual('{}'.format(index).encode(), example.example_id)
        self.assertEqual(150000000+index, example.event_time)
        self.assertEqual(index, example.index)
        expected_index = 501
        for (index, example) in visitor:
            self.assertEqual(index, expected_index)
            self.assertEqual('{}'.format(index).encode(), example.example_id)
            self.assertEqual(150000000+index, example.event_time)
            self.assertEqual(index, example.index)
            expected_index += 1
        self.assertEqual(self.end_index, index)

    def tearDown(self):
        if gfile.Exists(self.data_source.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source.example_dumped_dir)

if __name__ == '__main__':
    unittest.main()
