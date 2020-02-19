# Copyright 2020 The Fedlearner Authors. All Rights Reserved.
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
import random

import tensorflow as tf
from tensorflow.python.platform import gfile

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join import (
    data_block_manager, common, data_block_dumper,
    raw_data_manifest_manager, joiner_impl,
    example_id_dumper, customized_options
)

class TestExampleJoin(unittest.TestCase):
    def setUp(self):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-f"
        data_source.data_source_meta.partition_num = 1
        data_source.data_block_dir = "./data_block"
        data_source.example_dumped_dir = "./example_id"
        data_source.raw_data_dir = "./raw_data"
        data_source.data_source_meta.min_matching_window = 64
        data_source.data_source_meta.max_matching_window = 128
        data_source.data_source_meta.max_example_in_data_block = 128
        self.data_source = data_source
        if gfile.Exists(self.data_source.data_block_dir):
            gfile.DeleteRecursively(self.data_source.data_block_dir)
        if gfile.Exists(self.data_source.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source.example_dumped_dir)
        if gfile.Exists(self.data_source.raw_data_dir):
            gfile.DeleteRecursively(self.data_source.raw_data_dir)
        self.etcd = etcd_client.EtcdClient('test_cluster', 'localhost:2379',
                                           'fedlearner', True)
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)

    def generate_raw_data(self):
        dbm = data_block_manager.DataBlockManager(self.data_source, 0)
        raw_data_dir = os.path.join(self.data_source.raw_data_dir, 'partition_{}'.format(0))
        if gfile.Exists(raw_data_dir):
            gfile.DeleteRecursively(raw_data_dir)
        gfile.MakeDirs(raw_data_dir)
        self.total_index = 10 * 2048
        useless_index = 0
        for block_index in range(self.total_index // 2048):
            builder = data_block_manager.DataBlockBuilder(
                    self.data_source.raw_data_dir, 0, block_index, None
                )
            cands = list(range(block_index * 2048, (block_index + 1) * 2048))
            start_index = cands[0]
            for i in range(len(cands)):
                if random.randint(1, 4) > 2:
                    continue
                a = random.randint(i - 64, i + 64)
                b = random.randint(i - 64, i + 64)
                if a < 0:
                    a = 0
                if a >= len(cands):
                    a = len(cands) - 1
                if b < 0:
                    b = 0
                if b >= len(cands):
                    b = len(cands) - 1
                if (abs(cands[a]-i-start_index) <= 64 and
                        abs(cands[b]-i-start_index) <= 64):
                    cands[a], cands[b] = cands[b], cands[a]
            for example_idx in cands:
                feat = {}
                example_id = '{}'.format(example_idx).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = 150000000 + example_idx
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                builder.append(example.SerializeToString(), example_id,
                               event_time, useless_index, useless_index)
                useless_index += 1
            builder.finish_data_block()
        fpaths = [os.path.join(raw_data_dir, f)
                    for f in gfile.ListDirectory(raw_data_dir)
                    if not gfile.IsDirectory(os.path.join(raw_data_dir, f))]
        for fpath in fpaths:
            if not fpath.endswith(common.DataBlockSuffix):
                gfile.Remove(fpath)
        self.manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
                self.etcd, self.data_source
            )

    def generate_example_id(self):
        eid = example_id_dumper.ExampleIdDumperManager(self.data_source, 0)

        for req_index in range(self.total_index // 512):
            req = dj_pb.SyncExamplesRequest(
                    data_source_meta=self.data_source.data_source_meta,
                    partition_id=0,
                    begin_index=req_index * 512
                )
            cands = list(range(req_index * 512, (req_index + 1) * 512))
            start_index = cands[0]
            for i in range(len(cands)):
                if random.randint(1, 4) > 1:
                    continue
                a = random.randint(i - 32, i + 32)
                b = random.randint(i - 32, i + 32)
                if a < 0:
                    a = 0
                if a >= len(cands):
                    a = len(cands) - 1
                if b < 0:
                    b = 0
                if b >= len(cands):
                    b = len(cands) - 1
                if (abs(cands[a]-i-start_index) <= 32 and
                        abs(cands[b]-i-start_index) <= 32):
                    cands[a], cands[b] = cands[b], cands[a]
            for example_idx in cands:
                req.example_id.append('{}'.format(example_idx).encode())
                req.event_time.append(150000000 + example_idx)
            eid.append_synced_example_req(req)
            self.assertEqual(eid.get_next_index(), (req_index + 1) * 512)
        eid.finish_sync_example()
        self.assertTrue(eid.need_dump())
        eid.dump_example_ids()

    def test_example_join(self):
        self.generate_raw_data()
        self.generate_example_id()
        customized_options.set_example_joiner('STREAM_JOINER')
        sei = joiner_impl.create_example_joiner(
                self.etcd, self.data_source, 0
            )
        sei.join_example()
        self.assertTrue(sei.join_finished())
        dbm = data_block_manager.DataBlockManager(self.data_source, 0)
        data_block_num = dbm.get_dumped_data_block_num()
        join_count = 0
        for data_block_index in range(data_block_num):
            meta = dbm.get_data_block_meta_by_index(data_block_index)[0]
            self.assertTrue(meta is not None)
            join_count += len(meta.example_ids)

        print("join rate {}/{}({}), min_matching_window {}, "\
              "max_matching_window {}".format(
              join_count, self.total_index,
              (join_count+.0)/self.total_index,
              self.data_source.data_source_meta.min_matching_window,
              self.data_source.data_source_meta.max_matching_window))

    def tearDown(self):
        if gfile.Exists(self.data_source.data_block_dir):
            gfile.DeleteRecursively(self.data_source.data_block_dir)
        if gfile.Exists(self.data_source.example_dumped_dir):
            gfile.DeleteRecursively(self.data_source.example_dumped_dir)
        if gfile.Exists(self.data_source.raw_data_dir):
            gfile.DeleteRecursively(self.data_source.raw_data_dir)
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)

if __name__ == '__main__':
    unittest.main()
