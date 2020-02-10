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

from fedlearner.common import etcd_client
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb
from fedlearner.data_join import raw_data_manifest_manager

class TestRawDataManifestManager(unittest.TestCase):
    def test_raw_data_manifest_manager(self):
        cli = etcd_client.EtcdClient('test_cluster', 'localhost:2379',
                                     'fedlearner', True)
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-x"
        data_source.data_source_meta.partition_num = 4
        cli.delete_prefix(data_source.data_source_meta.name)
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            cli, data_source)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            self.assertEqual(
                manifest_map[i].state,
                dj_pb.RawDataState.UnAllocated
            )
            self.assertEqual(manifest_map[i].allocated_rank_id, -1)

        manifest, finished = manifest_manager.alloc_unallocated_partition(0)
        self.assertFalse(finished)
        partition_id = manifest.partition_id
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            if i != partition_id:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.UnAllocated
                )
                self.assertEqual(manifest_map[i].allocated_rank_id, -1)
            else:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.Syncing
                )
                self.assertEqual(manifest_map[i].allocated_rank_id, 0)

        manifest_manager.finish_sync_partition(0, partition_id)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            self.assertEqual(manifest_map[i].allocated_rank_id, -1)
            if i != partition_id:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.UnAllocated
                )
            else:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.Synced
                )
        manifest2, finished = manifest_manager.alloc_synced_partition(2)
        self.assertFalse(finished)
        self.assertEqual(manifest.partition_id, manifest2.partition_id)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            if i != partition_id:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.UnAllocated
                )
                self.assertEqual(manifest_map[i].allocated_rank_id, -1)
            else:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.Joining
                )
                self.assertEqual(manifest_map[i].allocated_rank_id, 2)
        manifest_manager.finish_join_partition(2, partition_id)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            self.assertEqual(manifest_map[i].allocated_rank_id, -1)
            if i != partition_id:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.UnAllocated
                )
            else:
                self.assertEqual(
                    manifest_map[i].state,
                    dj_pb.RawDataState.Done
                )
        cli.destory_client_pool()

if __name__ == '__main__':
    unittest.main()
