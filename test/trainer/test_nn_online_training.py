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
import fedlearner
import test_nn_trainer

import numpy as np
import unittest
import threading
import random
import os
import time
import logging
from multiprocessing import Process
import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile
from queue import PriorityQueue
import enum
from tensorflow.core.example.feature_pb2 import FloatList, Features, Feature, \
                                                Int64List, BytesList

from tensorflow.core.example.example_pb2 import Example

import numpy as np

from fedlearner.data_join import (
    data_block_manager, common,
    data_block_visitor, raw_data_manifest_manager
)

from fedlearner.common import (
    mysql_client, common_pb2 as common_pb,
    data_join_service_pb2 as dj_pb,
    trainer_master_service_pb2 as tm_pb
)

from fedlearner.data_join.data_block_manager import DataBlockBuilder
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

from fedlearner.trainer_master.leader_tm import LeaderTrainerMaster
from fedlearner.trainer_master.follower_tm import FollowerTrainerMaster
from fedlearner.data_join.common import get_kvstore_config



class TestDataSource(object):
    def __init__(self, base_path, name, role, partition_num=1,
                 start_time=0, end_time=100000):
        if role == 'leader':
            role = 0
        elif role == 'follower':
            role = 1
        else:
            raise ValueError("Unknown role %s"%role)
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = name
        data_source.data_source_meta.partition_num = partition_num
        data_source.data_source_meta.start_time = start_time
        data_source.data_source_meta.end_time = end_time
        data_source.output_base_dir = "{}/{}_{}/data_source/".format(
            base_path, data_source.data_source_meta.name, role)
        data_source.role = role
        if gfile.Exists(data_source.output_base_dir):
            gfile.DeleteRecursively(data_source.output_base_dir)

        self._data_source = data_source

        db_database, db_addr, db_username, db_password, db_base_dir = \
            get_kvstore_config("etcd")
        self._kv_store = mysql_client.DBClient(
            db_database, db_addr, db_username, db_password, db_base_dir, True)

        common.commit_data_source(self._kv_store, self._data_source)
        self._dbms = []
        for i in range(partition_num):
            manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
                self._kv_store, self._data_source)
            manifest_manager._finish_partition('join_example_rep',
                dj_pb.JoinExampleState.UnJoined, dj_pb.JoinExampleState.Joined,
                -1, i)
            self._dbms.append(
                data_block_manager.DataBlockManager(self._data_source, i))

    def add_data_block(self, partition_id, x, y):
        dbm = self._dbms[partition_id]

        builder = DataBlockBuilder(
            common.data_source_data_block_dir(self._data_source),
            self._data_source.data_source_meta.name, partition_id,
            dbm.get_dumped_data_block_count(),
            dj_pb.WriterOptions(output_writer="TF_RECORD"), None)
        builder.set_data_block_manager(dbm)
        for i in range(x.shape[0]):
            feat = {}
            exam_id = '{}'.format(i).encode()
            feat['example_id'] = Feature(
                bytes_list=BytesList(value=[exam_id]))
            feat['event_time'] = Feature(
                int64_list = Int64List(value=[i])
            )
            feat['x'] = Feature(float_list=FloatList(value=list(x[i])))
            if y is not None:
                feat['y'] = Feature(int64_list=Int64List(value=[y[i]]))

            example = Example(features=Features(feature=feat))
            builder.append_item(TfExampleItem(example.SerializeToString()), i, 0)

        return builder.finish_data_block()


class TestOnlineTraining(unittest.TestCase):
    def test_online_training(self):
        leader_ds = TestDataSource('./output', 'test_ds', 'leader')
        leader_ds.add_data_block(0, np.zeros((100, 10)), np.zeros((100,), dtype=np.int32))
        leader_tm = fedlearner.trainer_master.leader_tm.LeaderTrainerMaster(
            'leader_test', 'test_ds', None, None, True, False, 1)
        leader_thread = threading.Thread(target=leader_tm.run, args=(50051,))
        leader_thread.daemon = True
        leader_thread.start()

        follower_ds = TestDataSource('./output', 'test_ds', 'follower')
        follower_ds.add_data_block(0, np.zeros((100, 10)), np.zeros((100,), dtype=np.int32))
        follower_tm = fedlearner.trainer_master.follower_tm.FollowerTrainerMaster(
            'follower_test', 'test_ds', None, None, True)
        follower_thread = threading.Thread(target=follower_tm.run, args=(50052,))
        follower_thread.daemon = True
        follower_thread.start()

        leader_tmc = fedlearner.trainer.trainer_master_client.TrainerMasterClient(
            'localhost:50051', 'leader', 0)
        leader_tmc.restore_data_block_checkpoint('leader_test', [])
        block1 = leader_tmc.request_data_block().block_id
        self.assertEqual(block1, 'test_ds.partition_0000.00000000.0-99')
        leader_ds.add_data_block(0, np.zeros((100, 10)), np.zeros((100,), dtype=np.int32))
        block2 = leader_tmc.request_data_block().block_id
        self.assertEqual(block2, 'test_ds.partition_0000.00000001.0-99')

        follower_tmc = fedlearner.trainer.trainer_master_client.TrainerMasterClient(
            'localhost:50052', 'follower', 0)
        follower_tmc.restore_data_block_checkpoint('follower_test', [])
        self.assertEqual(block1, follower_tmc.request_data_block(block1).block_id)
        follower_ds.add_data_block(0, np.zeros((100, 10)), np.zeros((100,), dtype=np.int32))
        self.assertEqual(block2, follower_tmc.request_data_block(block2).block_id)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
