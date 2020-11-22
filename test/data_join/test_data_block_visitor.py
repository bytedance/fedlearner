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
import random

import tensorflow.compat.v1 as tf
tf.enable_eager_execution()
from google.protobuf import text_format
import tensorflow_io
from tensorflow.compat.v1 import gfile

from fedlearner.common import mysql_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import (
    data_block_manager, common,
    data_block_visitor, raw_data_manifest_manager
)
from fedlearner.data_join.data_block_manager import DataBlockBuilder
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

class TestDataBlockVisitor(unittest.TestCase):
    def setUp(self):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-x"
        data_source.data_source_meta.partition_num = 4
        data_source.data_source_meta.start_time = 0
        data_source.data_source_meta.end_time = 10000
        data_source.output_base_dir = "./ds_output"
        data_source.role = common_pb.FLRole.Follower
        self.data_source = data_source
        self.db_database = 'test_cluster'
        self.db_addr = 'localhost:2379'
        self.db_base_dir = 'fedlearner'
        self.db_username = 'test_user'
        self.db_password = 'test_password'
        self.kvstore = mysql_client.DBClient(self.db_database, self.db_addr,
                                              self.db_username, self.db_password,
                                              self.db_base_dir, True)
        common.commit_data_source(self.kvstore, self.data_source)
        if gfile.Exists(data_source.output_base_dir):
            gfile.DeleteRecursively(data_source.output_base_dir)
        self.data_block_matas = []
        self.manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.kvstore, self.data_source)
        partition_num = self.data_source.data_source_meta.partition_num
        for i in range(partition_num):
            self._create_data_block(i)

    def _create_data_block(self, partition_id):
        dbm = data_block_manager.DataBlockManager(self.data_source, partition_id)
        self.assertEqual(dbm.get_dumped_data_block_count(), 0)
        self.assertEqual(dbm.get_lastest_data_block_meta(), None)

        leader_index = 0
        follower_index = 65536
        for i in range(64):
            builder = DataBlockBuilder(
                    common.data_source_data_block_dir(self.data_source),
                    self.data_source.data_source_meta.name,
                    partition_id, i,
                    dj_pb.WriterOptions(output_writer='TF_RECORD'), None
                )
            builder.set_data_block_manager(dbm)
            for j in range(4):
                feat = {}
                example_id = '{}'.format(i * 1024 + j).encode()
                feat['example_id'] = tf.train.Feature(
                        bytes_list=tf.train.BytesList(value=[example_id]))
                event_time = random.randint(0, 10)
                feat['event_time'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[event_time]))
                feat['leader_index'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[leader_index]))
                feat['follower_index'] = tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[follower_index]))
                example = tf.train.Example(features=tf.train.Features(feature=feat))
                builder.append_item(TfExampleItem(example.SerializeToString()),
                                    leader_index, follower_index)
                leader_index += 1
                follower_index += 1
            self.data_block_matas.append(builder.finish_data_block())

    def test_data_block_visitor(self):
        self._test_round(10, 2, 4)
        self._test_round(63, 1, 7)

    def _test_round(self, dumped_index, start_time, end_time):
        partition_num = self.data_source.data_source_meta.partition_num
        for i in range(partition_num):
            self.manifest_manager.forward_peer_dumped_index(i, dumped_index)
        visitor = data_block_visitor.DataBlockVisitor(
                self.data_source.data_source_meta.name, self.db_database,
                self.db_base_dir, self.db_addr, self.db_username,
                self.db_password, True
            )
        reps = visitor.LoadDataBlockRepByTimeFrame(start_time, end_time)
        metas = [meta for meta in self.data_block_matas if
                    (not (meta.end_time > end_time or meta.end_time <= start_time) and
                        meta.data_block_index <= dumped_index)]
        self.assertEqual(len(reps), len(metas))
        for meta in metas:
            self.assertTrue(meta.block_id in reps)
            rep = reps[meta.block_id]
            self.assertEqual(meta.block_id, rep.block_id)
            self.assertEqual(meta.start_time, rep.start_time)
            self.assertEqual(meta.end_time, rep.end_time)
            self.assertEqual(meta.partition_id, rep.partition_id)
            self.assertEqual(meta, rep.data_block_meta)
            data_block_fpath = os.path.join(common.data_source_data_block_dir(self.data_source),
                                            common.partition_repr(meta.partition_id),
                                            meta.block_id + common.DataBlockSuffix)
            self.assertEqual(data_block_fpath, rep.data_block_fpath)

        for i in range(0, 100):
            rep = visitor.LoadDataBlockReqByIndex(random.randint(0, partition_num-1),
                                                  random.randint(0, dumped_index))
            try:
                meta = [meta for meta in self.data_block_matas if \
                        meta.block_id == rep.block_id][0]
            except Exception as e:
                print(e)
            self.assertEqual(meta.block_id, rep.block_id)
            self.assertEqual(meta.start_time, rep.start_time)
            self.assertEqual(meta.end_time, rep.end_time)
            self.assertEqual(meta.partition_id, rep.partition_id)
            self.assertEqual(meta, rep.data_block_meta)
            data_block_fpath = os.path.join(common.data_source_data_block_dir(self.data_source),
                                            common.partition_repr(meta.partition_id),
                                            meta.block_id + common.DataBlockSuffix)
            self.assertEqual(data_block_fpath, rep.data_block_fpath)
            self.assertIsNone(visitor.LoadDataBlockReqByIndex(random.randint(0, partition_num-1),
                                                              random.randint(dumped_index, 10000)))

    def tearDown(self):
        if gfile.Exists(self.data_source.output_base_dir):
            gfile.DeleteRecursively(self.data_source.output_base_dir)

if __name__ == '__main__':
    unittest.main()
