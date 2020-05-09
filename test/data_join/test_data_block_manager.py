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
from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import data_block_manager, common
from fedlearner.data_join.data_block_builder_impl \
        import create_data_block_builder

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
        self.assertEqual(self.data_block_manager.get_dumped_data_block_count(), 0)
        self.assertEqual(self.data_block_manager.get_lastest_data_block_meta(), None)

    def test_data_block_manager(self):
        data_block_datas = []
        data_block_metas = []
        leader_index = 0
        follower_index = 65536
        for i in range(5):
            fill_examples = []
            builder = create_data_block_builder(
                    dj_pb.DataBlockBuilderOptions(
                        data_block_builder='TF_RECORD_DATABLOCK_BUILDER'
                    ),
                    self.data_source.data_block_dir,
                    self.data_source.data_source_meta.name,
                    0, i, None
                )
            builder.set_data_block_manager(self.data_block_manager)
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
                builder.append_record(example.SerializeToString(), example_id,
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
            meta = builder.finish_data_block()
            data_block_datas.append(fill_examples)
            data_block_metas.append(meta)
        self.assertEqual(self.data_block_manager.get_dumped_data_block_count(), 5)
        self.assertEqual(self.data_block_manager.get_lastest_data_block_meta(),
                         data_block_metas[-1])
        for (idx, meta) in enumerate(data_block_metas):
            self.assertEqual(self.data_block_manager.get_data_block_meta_by_index(idx),
                             meta)
            self.assertEqual(meta.block_id, common.encode_block_id(
                    self.data_source.data_source_meta.name, meta
                )
            )
        self.assertEqual(self.data_block_manager.get_data_block_meta_by_index(5), None)
        data_block_dir = os.path.join(
                        self.data_source.data_block_dir, common.partition_repr(0)
                    )
        for (i, meta) in enumerate(data_block_metas):
            data_block_fpath = os.path.join(
                        data_block_dir, meta.block_id
                    ) + common.DataBlockSuffix
            data_block_meta_fpath = os.path.join(
                        data_block_dir, 
                        common.encode_data_block_meta_fname(
                            self.data_source.data_source_meta.name,
                            0, meta.data_block_index
                        )
                    )
            self.assertTrue(gfile.Exists(data_block_fpath))
            self.assertTrue(gfile.Exists(data_block_meta_fpath))
            fiter = tf.io.tf_record_iterator(data_block_meta_fpath)
            remote_meta = text_format.Parse(next(fiter).decode(), dj_pb.DataBlockMeta())
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

        data_block_manager2 = data_block_manager.DataBlockManager(
                self.data_source, 0
            )
        self.assertEqual(self.data_block_manager.get_dumped_data_block_count(), 5)

    def tearDown(self):
        if gfile.Exists(self.data_source.data_block_dir):
            gfile.DeleteRecursively(self.data_source.data_block_dir)

if __name__ == '__main__':
    unittest.main()
