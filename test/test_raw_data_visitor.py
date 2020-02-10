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
import ntpath

from tensorflow.python.platform import gfile
import tensorflow as tf

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import (
    raw_data_manifest_manager, raw_data_visitor, customized_options
)

class TestRawDataVisitor(unittest.TestCase):
    def setUp(self):
        self.data_source = common_pb.DataSource()
        self.data_source.data_source_meta.name = 'fclh_test'
        self.data_source.data_source_meta.partition_num = 1
        self.data_source.raw_data_dir = "./raw_data"
        self.etcd = etcd_client.EtcdClient('test_cluster', 'localhost:2379',
                                           'fedlearner', True)
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)
        self.assertEqual(self.data_source.data_source_meta.partition_num, 1)
        partition_dir = os.path.join(self.data_source.raw_data_dir, 'partition_0')
        if gfile.Exists(partition_dir):
            gfile.DeleteRecursively(partition_dir)
        gfile.MakeDirs(partition_dir)
        for i in range(2):
            fname = 'raw_data_{}'.format(i)
            fpath = os.path.join(partition_dir, fname)
            writer = tf.io.TFRecordWriter(fpath)
            for j in range(100):
                feat = {}
                example_id = '{}'.format(i * 100 + j).encode()
                feat['example_id'] = tf.train.Feature(
                                    bytes_list=tf.train.BytesList(
                                        value=[example_id]))
                example = tf.train.Example(
                    features=tf.train.Features(feature=feat))
                writer.write(example.SerializeToString())
            writer.close()

    def test_raw_data_manager(self):
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.etcd, self.data_source)
        rdm = raw_data_visitor.RawDataManager(self.etcd, self.data_source, 0)
        self.assertEqual(len(rdm.get_indexed_raw_data_reps()), 0)
        raw_data_rep0 = rdm.get_raw_data_rep_by_index(0)
        raw_data_rep1 = rdm.get_raw_data_rep_by_index(1)
        self.assertTrue(raw_data_rep0.HasField('unindexed'))
        self.assertTrue(raw_data_rep1.HasField('unindexed'))
        self.assertEqual(ntpath.basename(raw_data_rep0.raw_data_path), 'raw_data_0')
        self.assertEqual(ntpath.basename(raw_data_rep1.raw_data_path), 'raw_data_1')
        rdm.index_raw_data_rep(0, 0)
        self.assertEqual(len(rdm.get_indexed_raw_data_reps()), 1)
        indexed_rep0 = rdm.get_indexed_raw_data_reps()[0]
        self.assertEqual(indexed_rep0.raw_data_path, raw_data_rep0.raw_data_path)
        self.assertTrue(indexed_rep0.HasField('index'))
        self.assertEqual(indexed_rep0.index.start_index, 0)
        rdm.index_raw_data_rep(1, 100)
        self.assertEqual(len(rdm.get_indexed_raw_data_reps()), 2)
        indexed_rep1 = rdm.get_indexed_raw_data_reps()[1]
        self.assertEqual(indexed_rep1.raw_data_path, raw_data_rep1.raw_data_path)
        self.assertTrue(indexed_rep1.HasField('index'))
        self.assertEqual(indexed_rep1.index.start_index, 100)

    def test_raw_data_visitor(self):
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.etcd, self.data_source)
        manifest, finished = manifest_manager.alloc_unallocated_partition(2)
        self.assertFalse(finished)
        self.assertEqual(manifest.partition_id, 0)
        self.assertEqual(manifest.state, dj_pb.RawDataState.Syncing)
        self.assertEqual(manifest.allocated_rank_id, 2)
        customized_options.set_raw_data_iter('TF_RECORD')
        rdv = raw_data_visitor.RawDataVisitor(self.etcd, self.data_source, 0)
        expected_index = 0
        for (index, item) in rdv:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())
        try:
            rdv.seek(200)
        except StopIteration:
            self.assertTrue(True)
            self.assertEqual(rdv.get_current_index(), 199)
        else:
            self.assertFalse(False)
        index, item = rdv.seek(50)
        self.assertEqual(index, 50)
        self.assertEqual(item.example_id, '{}'.format(index).encode())
        expected_index = index + 1
        for (index, item) in rdv:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())

    def tearDown(self):
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)
        if gfile.Exists(self.data_source.raw_data_dir):
            gfile.DeleteRecursively(self.data_source.raw_data_dir)

if __name__ == '__main__':
    unittest.main()
