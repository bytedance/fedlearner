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
    example_id_dumper, example_id_visitor, data_block_manager, common
)

class TestDataBlockManager(unittest.TestCase):
    def setUp(self):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-x"
        data_source.data_source_meta.partition_num = 1
        data_source.data_block_dir = "./data_block"
        self.data_source = data_source
        if gfile.Exists(data_source.data_block_dir):
            gfile.DeleteRecursively(data_source.data_block_dir)
        self.data_block_manager = data_block_manager.DataBlockManager(
                data_source, 0
            )
        self.assertEqual(self.data_block_manager.get_dumped_data_block_num(), 0)
        self.assertEqual(self.data_block_manager.get_last_data_block_meta(), None)

    def test_data_block_manager(self):
        data_block_datas = []
        data_block_metas = []
        leader_index = 0
        follower_index = 65536
        for i in range(5):
            fill_examples = []
            builder = data_block_manager.DataBlockBuilder(
                    self.data_source.data_block_dir, 0, i, None
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
                fill_examples.append((example, {
                                'example_id': example_id, 
                                'event_time': event_time,
                                'leader_index': leader_index, 
                                'follower_index': follower_index
                            }
                        )
                    )
                leader_index += 1
                follower_index += 1
            builder.finish_data_block()
            data_block_datas.append(fill_examples)
            data_block_metas.append(builder.get_data_block_meta())
        self.assertEqual(self.data_block_manager.get_dumped_data_block_num(), 0)
        self.assertEqual(self.data_block_manager.get_last_data_block_meta(), None)
        self.assertEqual(self.data_block_manager.get_dumped_data_block_num(True), 5)
        for (idx, meta) in enumerate(data_block_metas):
            self.assertEqual(self.data_block_manager.get_data_block_meta_by_index(idx)[0], meta)
            self.assertEqual(meta.block_id, '{}-{}_{}'.format(
                             meta.start_time, meta.end_time, idx))
        self.assertEqual(self.data_block_manager.get_data_block_meta_by_index(5)[0], None)
        data_block_dir = os.path.join(
                        self.data_source.data_block_dir, 'partition_{}'.format(0)
                    )
        for (i, meta) in enumerate(data_block_metas):
            data_block_fpath = os.path.join(
                        data_block_dir, meta.block_id
                    ) + common.DataBlockSuffix
            data_block_meta_fpath = os.path.join(
                        data_block_dir, meta.block_id
                    ) + common.DataBlockMetaSuffix
            self.assertTrue(gfile.Exists(data_block_fpath))
            self.assertTrue(gfile.Exists(data_block_meta_fpath))
            fiter = tf.io.tf_record_iterator(data_block_meta_fpath)
            remote_meta = dj_pb.DataBlockMeta()
            remote_meta.ParseFromString(next(fiter))
            self.assertEqual(meta, remote_meta)
            for (j, record) in enumerate(tf.io.tf_record_iterator(data_block_fpath)):
                example = tf.train.Example()
                example.ParseFromString(record)
                stored_data = data_block_datas[i][j]
                self.assertEqual(example, stored_data[0])
                feat = example.features.feature
                stored_feat = stored_data[1]
                self.assertTrue('example_id' in feat)
                self.assertTrue('example_id' in stored_feat)
                self.assertEqual(stored_feat['example_id'], '{}'.format(i * 1024 + j).encode())
                self.assertEqual(stored_feat['example_id'],
                                 feat['example_id'].bytes_list.value[0])
                self.assertTrue('event_time' in feat)
                self.assertTrue('event_time' in stored_feat)
                self.assertEqual(stored_feat['event_time'],
                                 feat['event_time'].int64_list.value[0])
                self.assertTrue('leader_index' in feat)
                self.assertTrue('leader_index' in stored_feat)
                self.assertEqual(stored_feat['leader_index'],
                                 feat['leader_index'].int64_list.value[0])
                self.assertTrue('follower_index' in feat)
                self.assertTrue('follower_index' in stored_feat)
                self.assertEqual(stored_feat['follower_index'],
                                 feat['follower_index'].int64_list.value[0])
            self.assertEqual(j, 1023)

    def tearDown(self):
        if gfile.Exists(self.data_source.data_block_dir):
            gfile.DeleteRecursively(self.data_source.data_block_dir)

if __name__ == '__main__':
    unittest.main()
