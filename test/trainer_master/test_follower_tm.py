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

import logging
import unittest
import random
import tensorflow as tf

from tensorflow import gfile
from fedlearner.data_join import \
    raw_data_manifest_manager, data_block_manager, common
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import db_client
from fedlearner.trainer_master.follower_tm import FollowerTrainerMaster
from fedlearner.trainer.trainer_master_client import LocalTrainerMasterClient

class TestFollowerTrainerMaster(unittest.TestCase):
    def setUp(self):
        self._create_data_source()
        self._master = FollowerTrainerMaster(
            "test_app_id", self._data_source.data_source_meta.name)

    def _create_data_source(self):
        self._block_ids = []
        self._data_source = common_pb.DataSource()
        self._data_source.data_source_meta.name = \
            "test_follower_trainer_master_data_source"
        self._data_source.data_source_meta.partition_num = 2
        self._data_source.data_source_meta.start_time = 0
        self._data_source.data_source_meta.end_time = 10000
        self._data_source.output_base_dir = "./ds_output"
        self._data_source.role = common_pb.FLRole.Follower
        kvstore = db_client.DBClient('etcd', True)
        common.commit_data_source(kvstore, self._data_source)
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            kvstore, self._data_source)
        if gfile.Exists(self._data_source.output_base_dir):
            gfile.DeleteRecursively(self._data_source.output_base_dir)
        partition_num = self._data_source.data_source_meta.partition_num
        for partition_id in range(partition_num):
            dbm = data_block_manager.DataBlockManager(
                self._data_source, partition_id)
            leader_index = 0
            follower_index = 65536
            for i in range(4):
                builder = data_block_manager.DataBlockBuilder(
                        common.data_source_data_block_dir(self._data_source),
                        self._data_source.data_source_meta.name,
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
                            int64_list=tf.train.Int64List(
                                value=[follower_index]))
                    example = tf.train.Example(
                        features=tf.train.Features(feature=feat))
                    builder.append_item(
                        TfExampleItem(example.SerializeToString()),
                        leader_index, follower_index)
                    leader_index += 1
                    follower_index += 1
                builder.finish_data_block()
                self._block_ids.append(builder.get_data_block_meta().block_id)

            # rank_id ?
            #manifest_manager.finish_join_example

    def test_x(self):
        client = LocalTrainerMasterClient(self._master, 0)
        for block_id in self._block_ids:
            print(client.request_data_block(block_id))

    def tearDown(self):
        if gfile.Exists(self._data_source.output_base_dir):
            gfile.DeleteRecursively(self._data_source.output_base_dir)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)-15s [%(levelname)s]: %(message)s "
               "(%(filename)s:%(lineno)d)")
    unittest.main()
