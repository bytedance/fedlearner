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
tf.compat.v1.enable_eager_execution()

from fedlearner.common import etcd_client
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.data_join import (
    raw_data_manifest_manager, raw_data_visitor, customized_options
)

class TestRawDataVisitor(unittest.TestCase):
    def test_raw_data_visitor(self):
        self.data_source = common_pb.DataSource()
        self.data_source.data_source_meta.name = 'fclh_test'
        self.data_source.data_source_meta.partition_num = 1
        self.data_source.raw_data_dir = "./test/compressed_raw_data"
        self.etcd = etcd_client.EtcdClient('test_cluster', 'localhost:2379', 'fedlearner')
        self.etcd.delete_prefix(self.data_source.data_source_meta.name)
        self.assertEqual(self.data_source.data_source_meta.partition_num, 1)
        partition_dir = os.path.join(self.data_source.raw_data_dir, 'partition_0')
        self.assertTrue(gfile.Exists(partition_dir))
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            self.etcd, self.data_source)
        options = customized_options.CustomizedOptions()
        options.set_raw_data_iter('TF_DATASET')
        options.set_compressed_type('GZIP')
        rdv = raw_data_visitor.RawDataVisitor(self.etcd, self.data_source, 0, options)
        expected_index = 0
        for (index, item) in rdv:
            if index > 0 and index % 1024 == 0:
                print("{} {} {}".format(index, item.example_id, item.event_time))
            self.assertEqual(index, expected_index)
            expected_index += 1
        self.assertGreater(expected_index, 0)

if __name__ == '__main__':
    unittest.main()
