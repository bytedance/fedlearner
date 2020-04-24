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
import time
from os import path

import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile
from google.protobuf import timestamp_pb2

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import (
    raw_data_manifest_manager,
    raw_data_visitor, common, visitor
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
        partition_dir = os.path.join(self.data_source.raw_data_dir, common.partition_repr(0))
        if gfile.Exists(partition_dir):
            gfile.DeleteRecursively(partition_dir)
        gfile.MakeDirs(partition_dir)
        self.manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.etcd, self.data_source)

    def _gen_raw_data_file(self, start_index, end_index):
        partition_dir = os.path.join(self.data_source.raw_data_dir, common.partition_repr(0))
        fpaths = []
        for i in range(start_index, end_index):
            fname = "{}.rd".format(i)
            fpath = os.path.join(partition_dir, fname)
            fpaths.append(dj_pb.RawDataMeta(file_path=fpath,
                                      timestamp=timestamp_pb2.Timestamp(seconds=3)))
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
        self.manifest_manager.add_raw_data(0, fpaths, True)

    def test_raw_data_manager(self):
        rdm = raw_data_visitor.RawDataManager(self.etcd, self.data_source, 0)
        self.assertEqual(len(rdm.get_index_metas()), 0)
        self.assertFalse(rdm.check_index_meta_by_process_index(0))
        self._gen_raw_data_file(0, 2)
        self.assertEqual(len(rdm.get_index_metas()), 0)
        self.assertTrue(rdm.check_index_meta_by_process_index(0))
        self.assertTrue(rdm.check_index_meta_by_process_index(1))
        self.assertEqual(len(rdm.get_index_metas()), 0)
        partition_dir = os.path.join(self.data_source.raw_data_dir, common.partition_repr(0))
        index_meta0 = rdm.get_index_meta_by_index(0, 0)
        self.assertEqual(index_meta0.start_index, 0)
        self.assertEqual(index_meta0.process_index, 0)
        self.assertEqual(len(rdm.get_index_metas()), 1)
        index_meta1 = rdm.get_index_meta_by_index(1, 100)
        self.assertEqual(index_meta1.start_index, 100)
        self.assertEqual(index_meta1.process_index, 1)
        self.assertEqual(len(rdm.get_index_metas()), 2)
        self.assertFalse(rdm.check_index_meta_by_process_index(2))
        self._gen_raw_data_file(2, 4)
        self.assertTrue(rdm.check_index_meta_by_process_index(2))
        self.assertTrue(rdm.check_index_meta_by_process_index(3))
        index_meta2 = rdm.get_index_meta_by_index(2, 200)
        self.assertEqual(index_meta2.start_index, 200)
        self.assertEqual(index_meta2.process_index, 2)
        self.assertEqual(len(rdm.get_index_metas()), 3)
        index_meta3 = rdm.get_index_meta_by_index(3, 300)
        self.assertEqual(index_meta3.start_index, 300)
        self.assertEqual(index_meta3.process_index, 3)
        self.assertEqual(len(rdm.get_index_metas()), 4)

    def test_raw_data_visitor(self):
        rank_id = 2
        manifest = self.manifest_manager.alloc_sync_exampld_id(rank_id)
        self.assertEqual(manifest.partition_id, 0)
        self.assertEqual(manifest.sync_example_id_rep.state, dj_pb.SyncExampleIdState.Syncing)
        self.assertEqual(manifest.sync_example_id_rep.rank_id, rank_id)
        raw_data_options = dj_pb.RawDataOptions(raw_data_iter='TF_RECORD')
        rdv = raw_data_visitor.RawDataVisitor( 
                self.etcd, self.data_source,
                manifest.partition_id, raw_data_options
            )
        self.assertRaises(StopIteration, rdv.seek, 0)
        self.assertTrue(rdv.finished())
        self.assertFalse(rdv.is_visitor_stale())
        self._gen_raw_data_file(0, 2)
        self.assertTrue(rdv.is_visitor_stale())
        self.assertRaises(StopIteration, rdv.seek, 0)
        rdv.active_visitor()
        self.assertFalse(rdv.finished())
        expected_index = 0
        for (index, item) in rdv:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())
        self.assertEqual(expected_index, 200)
        self.assertRaises(StopIteration, rdv.seek, 200)
        self.assertTrue(rdv.finished())
        index, item = rdv.seek(50)
        self.assertEqual(index, 50)
        self.assertEqual(item.example_id, '{}'.format(index).encode())
        self.assertFalse(rdv.finished())
        expected_index = index + 1
        for (index, item) in rdv:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())
        self.assertEqual(expected_index, 200)
        self._gen_raw_data_file(2, 4)
        self.assertTrue(rdv.is_visitor_stale())
        self.assertTrue(rdv.finished())
        rdv.active_visitor()
        self.assertFalse(rdv.finished())
        for (index, item) in rdv:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())
        self.assertEqual(expected_index, 400)
        self.assertTrue(rdv.finished())
        rdv.reset()
        self.assertFalse(rdv.finished())
        expected_index = 0
        for (index, item) in rdv:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())
        self.assertEqual(expected_index, 400)
        self.assertTrue(rdv.finished())
        rdv2 = raw_data_visitor.RawDataVisitor( 
                self.etcd, self.data_source,
                manifest.partition_id, raw_data_options
            )
        expected_index = 0
        for (index, item) in rdv2:
            self.assertEqual(index, expected_index)
            expected_index += 1
            self.assertEqual(item.example_id, '{}'.format(index).encode())
        self.assertEqual(expected_index, 400)
        self.assertTrue(rdv2.finished())

    def tearDown(self):
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)
        if gfile.Exists(self.data_source.raw_data_dir):
            gfile.DeleteRecursively(self.data_source.raw_data_dir)

if __name__ == '__main__':
    unittest.main()
