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
    data_block_manager, common, data_block_dumper,
    raw_data_manifest_manager, customized_options
)

class TestDataBlockDumper(unittest.TestCase):
    def setUp(self):
        data_source_f = common_pb.DataSource()
        data_source_f.data_source_meta.name = "milestone-f"
        data_source_f.data_source_meta.partition_num = 1
        data_source_f.data_block_dir = "./data_block-f"
        self.data_source_f = data_source_f
        if gfile.Exists(self.data_source_f.data_block_dir):
            gfile.DeleteRecursively(self.data_source_f.data_block_dir)
        data_source_l = common_pb.DataSource()
        data_source_l.data_source_meta.name = "milestone-l"
        data_source_l.data_source_meta.partition_num = 1
        data_source_l.data_block_dir = "./data_block-l"
        data_source_l.raw_data_dir = "./raw_data-l"
        self.data_source_l = data_source_l
        if gfile.Exists(self.data_source_l.data_block_dir):
            gfile.DeleteRecursively(self.data_source_l.data_block_dir)
        if gfile.Exists(self.data_source_l.raw_data_dir):
            gfile.DeleteRecursively(self.data_source_l.raw_data_dir)
        self.etcd = etcd_client.EtcdClient('test_cluster', 'localhost:2379', 'fedlearner')
        self.etcd.delete_prefix(self.data_source_l.data_source_meta.name)


    def generate_follower_data_block(self):
        dbm = data_block_manager.DataBlockManager(self.data_source_f, 0)
        self.assertEqual(dbm.get_dumped_data_block_num(), 0)
        self.assertEqual(dbm.get_last_data_block_meta(), None)
        leader_index = 0
        follower_index = 65536
        self.dumped_metas = []
        for i in range(5):
            builder = data_block_manager.DataBlockBuilder(
                    self.data_source_f.data_block_dir, 0, i, None
                )
            for j in range(1024):
                feat = {}
                example_id = '{}'.format(i * 1024 + j).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = 150000000 + i * 1024 + j
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                feat['leader_index'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[leader_index]))
                feat['follower_index'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[follower_index]))
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                builder.append(example.SerializeToString(), example_id,
                               event_time, leader_index, follower_index)
                leader_index += 3
                follower_index += 1
            builder.finish_data_block()
            meta = builder.get_data_block_meta()
            self.dumped_metas.append(meta)
            dbm.add_dumped_data_block_meta(meta)
        self.leader_start_index = 0
        self.leader_end_index = leader_index
        self.assertEqual(dbm.get_dumped_data_block_num(True), 5)
        for (idx, meta) in enumerate(self.dumped_metas):
            self.assertEqual(dbm.get_data_block_meta_by_index(idx)[0], meta)
        self.assertEqual(dbm.get_dumped_data_block_num(True), 5)

    def generate_leader_raw_data(self):
        dbm = data_block_manager.DataBlockManager(self.data_source_l, 0)
        raw_data_dir = os.path.join(self.data_source_l.raw_data_dir, 'partition_{}'.format(0))
        if gfile.Exists(raw_data_dir):
            gfile.DeleteRecursively(raw_data_dir)
        gfile.MakeDirs(raw_data_dir)
        block_index = 0
        builder = data_block_manager.DataBlockBuilder(
                self.data_source_l.raw_data_dir, 0, block_index, None
        )
        for i in range(0, self.leader_end_index + 3):
            if i > 0 and i % 2048 == 0:
                builder.finish_data_block()
                block_index += 1
                builder = data_block_manager.DataBlockBuilder(
                        self.data_source_l.raw_data_dir, 0, block_index, None
                )
            feat = {}
            pt = i + 1 << 30
            if i % 3 == 0:
                pt = i // 3
            example_id = '{}'.format(pt).encode()
            feat['example_id'] = tf.train.Feature(
                    bytes_list=tf.train.BytesList(value=[example_id]))
            event_time = 150000000 + pt
            feat['event_time'] = tf.train.Feature(
                    int64_list=tf.train.Int64List(value=[event_time]))
            example = tf.train.Example(features=tf.train.Features(feature=feat))
            builder.append(example.SerializeToString(), example_id, event_time, i, i)
        builder.finish_data_block()
        fpaths = [os.path.join(raw_data_dir, f)
                    for f in gfile.ListDirectory(raw_data_dir)
                    if not gfile.IsDirectory(os.path.join(raw_data_dir, f))]
        for fpath in fpaths:
            if not fpath.endswith(common.DataBlockSuffix):
                gfile.Remove(fpath)
        self.manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
                self.etcd, self.data_source_l
            )

        
    def test_data_block_dumper(self):
        self.generate_follower_data_block()
        self.generate_leader_raw_data()
        options = customized_options.CustomizedOptions()
        options.set_raw_data_iter('TF_RECORD')
        dbd = data_block_dumper.DataBlockDumperManager(
                self.etcd, self.data_source_l, 0, options
            )
        self.assertEqual(dbd.get_partition_id(), 0)
        self.assertEqual(dbd.get_next_data_block_index(), 0)
        for (idx, meta) in enumerate(self.dumped_metas):
            success, next_index = dbd.append_synced_data_block_meta(meta)
            self.assertTrue(success)
            self.assertEqual(next_index, idx + 1)
        self.assertTrue(dbd.need_dump())
        self.assertEqual(dbd.get_next_data_block_index(), len(self.dumped_metas))
        dbd.dump_data_blocks()
        dbm_f = data_block_manager.DataBlockManager(self.data_source_f, 0)
        dbm_l = data_block_manager.DataBlockManager(self.data_source_l, 0)
        self.assertEqual(dbm_f.get_dumped_data_block_num(), len(self.dumped_metas))
        self.assertEqual(dbm_f.get_dumped_data_block_num(),
                            dbm_l.get_dumped_data_block_num())
        for (idx, meta) in enumerate(self.dumped_metas):
            self.assertEqual(meta.data_block_index, idx)
            self.assertEqual(dbm_l.get_data_block_meta_by_index(idx)[0], meta)
            self.assertEqual(dbm_f.get_data_block_meta_by_index(idx)[0], meta)
            block_id = meta.block_id
            meta_fpth_l = os.path.join(self.data_source_l.data_block_dir, 'partition_0',
                                       block_id + common.DataBlockMetaSuffix)
            mitr = tf.io.tf_record_iterator(meta_fpth_l)
            meta_l = dj_pb.DataBlockMeta()
            meta_l.ParseFromString(next(mitr))
            self.assertEqual(meta_l, meta)
            meta_fpth_f = os.path.join(self.data_source_f.data_block_dir, 'partition_0',
                                       block_id + common.DataBlockMetaSuffix)
            mitr = tf.io.tf_record_iterator(meta_fpth_f)
            meta_f = dj_pb.DataBlockMeta()
            meta_f.ParseFromString(next(mitr)) 
            self.assertEqual(meta_f, meta)
            data_fpth_l = os.path.join(self.data_source_l.data_block_dir, 'partition_0',
                                       block_id + common.DataBlockSuffix)
            for (iidx, record) in enumerate(tf.io.tf_record_iterator(data_fpth_l)):
                example = tf.train.Example()
                example.ParseFromString(record)
                feat = example.features.feature
                self.assertEqual(feat['example_id'].bytes_list.value[0],
                                 meta.example_ids[iidx])
            self.assertEqual(len(meta.example_ids), iidx + 1)
            data_fpth_f = os.path.join(self.data_source_f.data_block_dir, 'partition_0',
                                       block_id + common.DataBlockSuffix)
            for (iidx, record) in enumerate(tf.io.tf_record_iterator(data_fpth_f)):
                example = tf.train.Example()
                example.ParseFromString(record)
                feat = example.features.feature
                self.assertEqual(feat['example_id'].bytes_list.value[0],
                                 meta.example_ids[iidx])
            self.assertEqual(len(meta.example_ids), iidx + 1)

    def tearDown(self):
        if gfile.Exists(self.data_source_f.data_block_dir):
            gfile.DeleteRecursively(self.data_source_f.data_block_dir)
        if gfile.Exists(self.data_source_l.data_block_dir):
            gfile.DeleteRecursively(self.data_source_l.data_block_dir)
        if gfile.Exists(self.data_source_l.raw_data_dir):
            gfile.DeleteRecursively(self.data_source_l.raw_data_dir)
        self.etcd.delete_prefix(self.data_source_l.data_source_meta.name)

if __name__ == '__main__':
    unittest.main()
