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

from google.protobuf import timestamp_pb2
from tensorflow.compat.v1 import gfile
import tensorflow.compat.v1 as tf
tf.enable_eager_execution()

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import raw_data_manifest_manager, raw_data_visitor, common

class TestRawDataVisitor(unittest.TestCase):
    def test_raw_data_visitor(self):
        self.data_source = common_pb.DataSource()
        self.data_source.data_source_meta.name = 'fclh_test'
        self.data_source.data_source_meta.partition_num = 1
        self.data_source.raw_data_dir = "./test/compressed_raw_data"
        self.etcd = etcd_client.EtcdClient('test_cluster', 'localhost:2379',
                                           'fedlearner', True)
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)
        self.assertEqual(self.data_source.data_source_meta.partition_num, 1)
        partition_dir = os.path.join(self.data_source.raw_data_dir, common.partition_repr(0))
        self.assertTrue(gfile.Exists(partition_dir))
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.etcd, self.data_source)
        manifest_manager.add_raw_data(
                0, [dj_pb.RawDataMeta(file_path=os.path.join(partition_dir, "0-0.idx"),
                                      timestamp=timestamp_pb2.Timestamp(seconds=3))],
                True)
        raw_data_options = dj_pb.RawDataOptions(
                raw_data_iter='TF_DATASET',
                compressed_type='GZIP'
            )
        rdm = raw_data_visitor.RawDataManager(self.etcd, self.data_source,0)
        self.assertTrue(rdm.check_index_meta_by_process_index(0))
        rdv = raw_data_visitor.RawDataVisitor(self.etcd, self.data_source, 0,
                                              raw_data_options)
        expected_index = 0
        for (index, item) in rdv:
            if index > 0 and index % 32 == 0:
                print("{} {}".format(index, item.example_id))
            self.assertEqual(index, expected_index)
            expected_index += 1
        self.assertGreater(expected_index, 0)

if __name__ == '__main__':
    unittest.main()
